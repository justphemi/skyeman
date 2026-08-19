"""Operations console views — a simple, friendly staff dashboard at /manage/.

Separate from Django admin. Pages:
  /manage/                — KPIs + recent activity
  /manage/bookings/       — all bookings (filter by status, date)
  /manage/dropzones/      — drop zones & slots
  /manage/users/          — user accounts
  /manage/payments/       — payments log
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import staff_required
from bookings.models import Booking, Payment, BookingParticipant
from dropzones.models import DropZone, TimeSlot, JumpPackage


User = get_user_model()


@staff_required
def dashboard(request):
    today = date.today()
    week_ahead = today + timedelta(days=7)
    last_30 = today - timedelta(days=30)

    kpis = {
        "today_count": Booking.objects.filter(time_slot__date=today).exclude(status="cancelled").count(),
        "week_count": Booking.objects.filter(
            time_slot__date__gte=today, time_slot__date__lte=week_ahead
        ).exclude(status="cancelled").count(),
        "pending_count": Booking.objects.filter(status="pending").count(),
        "cancelled_30d": Booking.objects.filter(
            status="cancelled", created_at__date__gte=last_30
        ).count(),
        "revenue_30d": Payment.objects.filter(
            status="paid", paid_at__date__gte=last_30
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0"),
        "total_users": User.objects.count(),
        "total_dropzones": DropZone.objects.count(),
        "open_slots_week": TimeSlot.objects.filter(
            date__gte=today, date__lte=week_ahead, status="open"
        ).count(),
    }

    recent_bookings = (
        Booking.objects
        .select_related("user", "time_slot__drop_zone", "package", "payment")
        .order_by("-created_at")[:8]
    )
    upcoming_slots = (
        TimeSlot.objects
        .filter(date__gte=today, date__lte=week_ahead, status="open")
        .select_related("drop_zone")
        .order_by("date", "start_time")[:8]
    )
    recent_payments = (
        Payment.objects
        .select_related("booking__user", "booking__time_slot__drop_zone")
        .order_by("-paid_at")[:5]
    )

    return render(request, "manage_ui/dashboard.html", {
        "kpis": kpis,
        "recent_bookings": recent_bookings,
        "upcoming_slots": upcoming_slots,
        "recent_payments": recent_payments,
        "today": today,
    })


@staff_required
def bookings_list(request):
    status_filter = request.GET.get("status", "")
    date_from = request.GET.get("from", "")
    date_to = request.GET.get("to", "")

    qs = (
        Booking.objects
        .select_related("user", "time_slot__drop_zone", "package", "payment")
        .order_by("-created_at")
    )
    if status_filter in ["pending", "confirmed", "cancelled", "completed"]:
        qs = qs.filter(status=status_filter)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    counts = {
        "all": Booking.objects.count(),
        "pending": Booking.objects.filter(status="pending").count(),
        "confirmed": Booking.objects.filter(status="confirmed").count(),
        "completed": Booking.objects.filter(status="completed").count(),
        "cancelled": Booking.objects.filter(status="cancelled").count(),
    }

    return render(request, "manage_ui/bookings.html", {
        "bookings": qs[:200],
        "counts": counts,
        "selected_status": status_filter,
        "date_from": date_from,
        "date_to": date_to,
    })


@staff_required
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related(
            "user", "time_slot__drop_zone", "package", "payment"
        ),
        pk=pk,
    )
    participants = booking.participants.all()
    return render(request, "manage_ui/booking_detail.html", {
        "booking": booking,
        "participants": participants,
    })


@staff_required
@require_POST
def booking_action(request, pk):
    """Mark a booking as confirmed / completed / cancelled from the console."""
    booking = get_object_or_404(Booking, pk=pk)
    action = request.POST.get("action", "")
    if action in ("confirm", "complete", "cancel"):
        booking.status = {"confirm": "confirmed", "complete": "completed", "cancel": "cancelled"}[action]
        booking.save()
        booking.time_slot.update_status()
        if action == "cancel" and hasattr(booking, "payment") and booking.payment.status == "paid":
            booking.payment.status = "refunded"
            booking.payment.save()
        messages.success(request, f"Booking #{booking.pk} marked as {booking.get_status_display()}.")
    else:
        messages.error(request, "Unknown action.")
    return redirect("manage_ui:booking_detail", pk=pk)


@staff_required
def dropzones_list(request):
    drop_zones = (
        DropZone.objects
        .annotate(slots_total=Count("time_slots", distinct=True))
        .order_by("name")
    )
    return render(request, "manage_ui/dropzones.html", {"drop_zones": drop_zones})


@staff_required
def users_list(request):
    users = User.objects.annotate(bookings_count=Count("bookings")).order_by("-date_joined")[:200]
    return render(request, "manage_ui/users.html", {"users": users})


@staff_required
def payments_list(request):
    status_filter = request.GET.get("status", "")
    qs = (
        Payment.objects
        .select_related("booking__user", "booking__time_slot__drop_zone")
        .order_by("-paid_at")
    )
    if status_filter in ["pending", "paid", "refunded", "failed"]:
        qs = qs.filter(status=status_filter)
    total_paid = qs.filter(status="paid").aggregate(t=Sum("amount"))["t"] or Decimal("0")
    return render(request, "manage_ui/payments.html", {
        "payments": qs[:200],
        "selected_status": status_filter,
        "total_paid": total_paid,
    })


# ---------------------------------------------------------------------------
# Slot calendar (/manage/slots/) — operations team sets availability here
# ---------------------------------------------------------------------------

@staff_required
def slots_list(request):
    """Date-grouped list of all slots. Filter by drop zone, status, date range."""
    zone_id = request.GET.get("zone", "")
    status_filter = request.GET.get("status", "")
    qs = TimeSlot.objects.select_related("drop_zone").order_by("date", "start_time")
    if zone_id:
        qs = qs.filter(drop_zone_id=zone_id)
    if status_filter in ["open", "full", "cancelled"]:
        qs = qs.filter(status=status_filter)

    grouped = {}
    for s in qs:
        grouped.setdefault(s.date, []).append(s)

    drop_zones = DropZone.objects.all()
    counts = {
        "open": TimeSlot.objects.filter(status="open").count(),
        "full": TimeSlot.objects.filter(status="full").count(),
        "cancelled": TimeSlot.objects.filter(status="cancelled").count(),
        "all": TimeSlot.objects.count(),
    }
    return render(request, "manage_ui/slots.html", {
        "grouped_slots": grouped,
        "drop_zones": drop_zones,
        "selected_zone": zone_id,
        "selected_status": status_filter,
        "counts": counts,
        "today": date.today(),
    })


@staff_required
def slot_create(request):
    """Quick-create form for a new time slot."""
    if request.method == "POST":
        dz_id = request.POST.get("drop_zone")
        date_str = request.POST.get("date")
        time_str = request.POST.get("start_time")
        capacity = request.POST.get("capacity") or 8
        if not (dz_id and date_str and time_str):
            messages.error(request, "Drop zone, date and start time are required.")
        else:
            try:
                from datetime import datetime as _dt
                slot_dt = _dt.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                slot, created = TimeSlot.objects.get_or_create(
                    drop_zone_id=dz_id,
                    date=slot_dt.date(),
                    start_time=slot_dt.time(),
                    defaults={"capacity": int(capacity), "status": "open"},
                )
                if created:
                    messages.success(request, f"Slot created: {slot}.")
                else:
                    messages.info(request, f"That slot already exists: {slot}.")
            except ValueError as e:
                messages.error(request, f"Invalid date or time: {e}")
        return redirect("manage_ui:slots")
    return render(request, "manage_ui/slot_form.html", {"drop_zones": DropZone.objects.all()})


@staff_required
@require_POST
def slot_action(request, pk):
    """One-click status changes for a slot from the calendar list."""
    slot = get_object_or_404(TimeSlot, pk=pk)
    action = request.POST.get("action", "")
    if action == "open":
        slot.status = "open"
        messages.success(request, f"Slot {slot} is now open.")
    elif action == "full":
        slot.status = "full"
        messages.info(request, f"Slot {slot} marked as full.")
    elif action == "cancel":
        slot.status = "cancelled"
        messages.warning(request, f"Slot {slot} cancelled (weather / ops).")
    elif action == "delete":
        slot.delete()
        messages.success(request, "Slot removed.")
        return redirect("manage_ui:slots")
    else:
        messages.error(request, "Unknown action.")
    slot.save()
    return redirect("manage_ui:slots")
