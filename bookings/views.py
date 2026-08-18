"""Bookings app — customer-facing views for the booking wizard, payment, and management.

Booking flow:
  /bookings/book/step-1/   pick drop zone
  /bookings/book/step-2/   pick package
  /bookings/book/step-3/   pick available time slot
  /bookings/book/step-4/   jumper details (age, weight, companions)
  -> /bookings/<id>/pay/   simulated payment
  -> /bookings/<id>/confirmation/
"""
from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from dropzones.models import DropZone, JumpPackage, TimeSlot
from .models import Booking, Payment, BookingParticipant
from .forms import BookingDetailsForm


# ---------------------------------------------------------------------------
# Booking wizard — 4 steps, state lives in the URL
# ---------------------------------------------------------------------------

def _parse_int_qs(request, key):
    """Pull an int query param safely; return None if missing/invalid."""
    raw = request.GET.get(key) or request.POST.get(key)
    if not raw or not raw.isdigit():
        return None
    return int(raw)


@login_required
def booking_step_dropzone(request):
    """Step 1: pick a drop zone."""
    drop_zones = DropZone.objects.prefetch_related("time_slots").all()
    selected_id = _parse_int_qs(request, "dropzone")

    if request.method == "POST":
        selected_id = _parse_int_qs(request, "dropzone")
        if not selected_id or not DropZone.objects.filter(pk=selected_id).exists():
            messages.error(request, "Please pick a drop zone.")
        else:
            return redirect(f"{request.path}step-2/?dropzone={selected_id}")
    return render(request, "bookings/booking_step_dropzone.html", {
        "drop_zones": drop_zones,
        "selected_id": selected_id,
        "step": 1,
        "total_steps": 4,
    })


@login_required
def booking_step_package(request):
    """Step 2: pick a package. Requires dropzone from step 1."""
    dropzone_id = _parse_int_qs(request, "dropzone")
    dropzone = get_object_or_404(DropZone, pk=dropzone_id) if dropzone_id else None
    if not dropzone:
        messages.error(request, "Pick a drop zone first.")
        return redirect("bookings:step_dropzone")

    packages = JumpPackage.objects.all()
    selected_id = _parse_int_qs(request, "package")

    if request.method == "POST":
        selected_id = _parse_int_qs(request, "package")
        if not selected_id or not JumpPackage.objects.filter(pk=selected_id).exists():
            messages.error(request, "Please pick a package.")
        else:
            return redirect(f"{request.path}step-3/?dropzone={dropzone.pk}&package={selected_id}")

    return render(request, "bookings/booking_step_package.html", {
        "dropzone": dropzone,
        "packages": packages,
        "selected_id": selected_id,
        "step": 2,
        "total_steps": 4,
    })


@login_required
def booking_step_slot(request):
    """Step 3: pick an available time slot. Requires dropzone + package."""
    dropzone_id = _parse_int_qs(request, "dropzone")
    package_id = _parse_int_qs(request, "package")
    dropzone = get_object_or_404(DropZone, pk=dropzone_id) if dropzone_id else None
    package = get_object_or_404(JumpPackage, pk=package_id) if package_id else None
    if not dropzone or not package:
        messages.error(request, "Pick a drop zone and package first.")
        return redirect("bookings:step_dropzone")

    slots = (
        TimeSlot.objects
        .filter(date__gte=date.today(), status="open", drop_zone=dropzone)
        .filter(bookings__isnull=True)  # placeholder, real filter below
        .order_by("date", "start_time")
    )
    # Filter to slots with seats and in the future
    slots = [s for s in slots if s.is_available and s.seats_left > 0]

    # Group by date for the UI
    grouped = {}
    for s in slots:
        grouped.setdefault(s.date, []).append(s)

    selected_id = _parse_int_qs(request, "slot")

    if request.method == "POST":
        selected_id = _parse_int_qs(request, "slot")
        if not selected_id:
            messages.error(request, "Please pick a time slot.")
        else:
            slot = TimeSlot.objects.filter(pk=selected_id, drop_zone=dropzone).first()
            if not slot or not slot.is_available or slot.seats_left <= 0:
                messages.error(request, "That time slot isn't available anymore — please pick another.")
            else:
                return redirect(
                    f"{request.path}step-4/?dropzone={dropzone.pk}&package={package.pk}&slot={slot.pk}"
                )

    return render(request, "bookings/booking_step_slot.html", {
        "dropzone": dropzone,
        "package": package,
        "grouped_slots": grouped,
        "selected_id": selected_id,
        "step": 3,
        "total_steps": 4,
    })


@login_required
def booking_step_details(request):
    """Step 4: jumper details (age, weight, group size, companions). Final submission."""
    dropzone_id = _parse_int_qs(request, "dropzone")
    package_id = _parse_int_qs(request, "package")
    slot_id = _parse_int_qs(request, "slot")
    dropzone = get_object_or_404(DropZone, pk=dropzone_id) if dropzone_id else None
    package = get_object_or_404(JumpPackage, pk=package_id) if package_id else None
    slot = get_object_or_404(TimeSlot, pk=slot_id) if slot_id else None
    if not dropzone or not package or not slot:
        messages.error(request, "Please start the booking again.")
        return redirect("bookings:step_dropzone")
    if not slot.is_available or slot.seats_left <= 0:
        messages.error(request, "That time slot just filled up. Please pick another.")
        return redirect(f"{reverse('bookings:step_slot')}?dropzone={dropzone.pk}&package={package.pk}")

    if request.method == "POST":
        form = BookingDetailsForm(request.POST, package=package, slot=slot)
        if form.is_valid():
            companions = form.cleaned_data.pop("_companions", [])
            booking = form.save(commit=False)
            booking.user = request.user
            booking.status = "pending"
            booking.save()

            BookingParticipant.objects.create(
                booking=booking,
                full_name=request.user.get_full_name() or request.user.username,
                age=booking.jumper_age or 18,
                weight_kg=booking.jumper_weight_kg,
                is_lead=True,
            )
            for c in companions:
                BookingParticipant.objects.create(
                    booking=booking,
                    full_name=c["full_name"],
                    age=c["age"],
                    weight_kg=c.get("weight_kg"),
                    is_lead=False,
                )
            slot.update_status()

            count = booking.participants.count()
            msg = f"Slot held for {count} jumper(s). Complete payment to confirm."
            messages.success(request, msg)
            return redirect("bookings:pay", pk=booking.pk)
    else:
        form = BookingDetailsForm(package=package, slot=slot)

    return render(request, "bookings/booking_step_details.html", {
        "dropzone": dropzone,
        "package": package,
        "slot": slot,
        "form": form,
        "step": 4,
        "total_steps": 4,
    })


# ---------------------------------------------------------------------------
# Existing detail / pay / reschedule / cancel / confirmation views
# ---------------------------------------------------------------------------

@login_required
def my_bookings(request):
    bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related("time_slot__drop_zone", "package", "payment")
        .order_by("-created_at")
    )
    confirmed_count = bookings.filter(status="confirmed").count()
    pending_count = bookings.filter(status="pending").count()
    return render(request, "bookings/my_bookings.html", {
        "bookings": bookings,
        "confirmed_count": confirmed_count,
        "pending_count": pending_count,
    })


@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("time_slot__drop_zone", "package", "payment", "user"),
        pk=pk, user=request.user,
    )
    return render(request, "bookings/booking_detail.html", {"booking": booking})


@login_required
def booking_pay(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("time_slot__drop_zone", "package"),
        pk=pk, user=request.user,
    )
    if hasattr(booking, "payment") and booking.payment.status == "paid":
        messages.info(request, "This booking has already been paid and confirmed.")
        return redirect("bookings:detail", pk=booking.pk)

    from .forms import PaymentForm
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            method = form.cleaned_data.get("method", "card")
            Payment.objects.update_or_create(
                booking=booking,
                defaults={
                    "amount": booking.total_price,
                    "method": method,
                    "status": "paid",
                    "paid_at": timezone.now(),
                },
            )
            booking.status = "confirmed"
            booking.save()
            booking.time_slot.update_status()
            messages.success(request, f"Payment simulated. Your {booking.package.name} jump is confirmed.")
            return redirect("bookings:confirmation", pk=booking.pk)
    else:
        form = PaymentForm()

    return render(request, "bookings/booking_pay.html", {"form": form, "booking": booking})


@login_required
def booking_confirmation(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("time_slot__drop_zone", "package", "payment"),
        pk=pk, user=request.user,
    )
    return render(request, "bookings/booking_confirmation.html", {"booking": booking})


@login_required
def booking_reschedule(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("time_slot__drop_zone", "package"),
        pk=pk, user=request.user,
    )
    if not booking.is_reschedulable:
        messages.error(request, "This booking cannot be rescheduled.")
        return redirect("bookings:detail", pk=booking.pk)

    from .forms import RescheduleBookingForm
    if request.method == "POST":
        form = RescheduleBookingForm(request.POST, booking=booking)
        if form.is_valid():
            old_slot = booking.time_slot
            new_slot = form.cleaned_data["new_time_slot"]
            booking.time_slot = new_slot
            booking.save()
            old_slot.update_status()
            new_slot.update_status()
            messages.success(request, f"Rescheduled to {new_slot.date.strftime('%B %d, %Y')} at {new_slot.start_time.strftime('%I:%M %p')}.")
            return redirect("bookings:detail", pk=booking.pk)
    else:
        form = RescheduleBookingForm(booking=booking)

    return render(request, "bookings/booking_reschedule.html", {"form": form, "booking": booking})


@login_required
def booking_cancel(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("time_slot__drop_zone", "package"),
        pk=pk, user=request.user,
    )
    if not booking.is_cancellable:
        messages.error(request, "This booking can no longer be cancelled.")
        return redirect("bookings:detail", pk=booking.pk)

    if request.method == "POST":
        booking.status = "cancelled"
        booking.save()
        booking.time_slot.update_status()
        if hasattr(booking, "payment") and booking.payment.status == "paid":
            booking.payment.status = "refunded"
            booking.payment.save()
            messages.success(request, f"Booking cancelled. ₦{booking.payment.amount:,.0f} refund processed.")
        else:
            messages.success(request, "Booking reservation cancelled.")
        return redirect("bookings:my_bookings")

    return render(request, "bookings/booking_cancel.html", {"booking": booking})
