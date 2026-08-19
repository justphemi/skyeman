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
            return redirect(f"{reverse('bookings:step_package')}?dropzone={selected_id}")
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
            return redirect(f"{reverse('bookings:step_slot')}?dropzone={dropzone.pk}&package={selected_id}")

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
                    f"{reverse('bookings:step_details')}?dropzone={dropzone.pk}&package={package.pk}&slot={slot.pk}"
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
            booking.package = package
            booking.time_slot = slot
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


@login_required
def booking_ticket_svg(request, pk):
    """Generate a Skyeman-styled booking confirmation ticket for download.

    Query string ?format=svg|png|jpg controls the output. Default is png.
    Rasterization uses Pillow (we render the layout natively in PIL instead of
    rasterizing the SVG, so the output is identical across machines without
    needing cairosvg or headless browsers).
    """
    booking = get_object_or_404(
        Booking.objects.select_related("time_slot__drop_zone", "package", "payment", "user"),
        pk=pk, user=request.user,
    )
    if booking.status not in ("confirmed", "completed"):
        messages.error(request, "Ticket is only available for confirmed bookings.")
        return redirect("bookings:detail", pk=booking.pk)

    fmt = request.GET.get("format", "png").lower()
    if fmt not in ("svg", "png", "jpg", "jpeg"):
        fmt = "png"

    b = booking
    jumper_name = (b.user.get_full_name() or b.user.username).strip()
    zone = b.time_slot.drop_zone.name
    zone_city = b.time_slot.drop_zone.city
    pkg_name = b.package.name
    when = b.time_slot.date.strftime("%b %d, %Y")
    time_ = b.time_slot.start_time.strftime("%I:%M %p").lstrip("0")
    amount = f"₦{b.total_price:,.0f}"
    ref = f"SKY-{b.pk:06d}"
    issued = date.today().strftime("%b %d, %Y")
    group_label = f"{b.group_size} jumper{'s' if b.group_size != 1 else ''}"

    from django.http import HttpResponse

    if fmt == "svg":
        svg = _build_ticket_svg(jumper_name, zone, zone_city, pkg_name, when, time_,
                                amount, ref, issued, group_label)
        resp = HttpResponse(svg, content_type="image/svg+xml")
        resp["Content-Disposition"] = f'attachment; filename="skyeman-ticket-{ref}.svg"'
        return resp

    # ---- PNG / JPEG: render natively with Pillow ----
    from PIL import Image, ImageDraw, ImageFont
    W, H = 880, 360
    img = Image.new("RGB", (W, H), (11, 15, 23))
    draw = ImageDraw.Draw(img)

    # Gradient background (top-left dark -> bottom-right slightly lighter)
    for y in range(H):
        for x in range(W):
            t = (x + y) / (W + H)
            r = int(11 + (20 - 11) * t)
            g = int(15 + (26 - 15) * t)
            b_ = int(23 + (38 - 23) * t)
            draw.point((x, y), fill=(r, g, b_))

    # Subtle dot pattern
    for y in range(20, H, 22):
        for x in range(20, W, 22):
            draw.ellipse((x-1, y-1, x+1, y+1), fill=(35, 45, 63))

    # Outer border
    draw.rounded_rectangle((6, 6, W-6, H-6), radius=18, outline=(31, 39, 55), width=2)

    # Orange accent stripe (left edge)
    for i in range(6):
        draw.rectangle((i, 0, i+1, H), fill=(255 - i*4, 106 + i*8, 26 + i*4))

    # ---- Logo + brand ----
    # Glowing orange circle
    for r, alpha in [(28, 30), (24, 50), (20, 80)]:
        draw.ellipse((36-r+18, 36-r+18, 36+r+18, 36+r+18),
                     fill=(255, 122, 30))
    draw.ellipse((36, 36, 72, 72), fill=(255, 106, 26))
    # Star inside logo
    star = [(54, 42), (57, 50), (65, 50), (59, 55), (61, 63),
            (54, 58), (47, 63), (49, 55), (43, 50), (51, 50)]
    draw.polygon(star, fill=(255, 255, 255))
    # Brand text
    f_brand_big = _pil_font(22, bold=True)
    f_brand_sub = _pil_font(11)
    draw.text((90, 44), "skyeman", font=f_brand_big, fill=(255, 255, 255))
    bbox = draw.textbbox((0, 0), "skyeman", font=f_brand_big)
    draw.text((90 + (bbox[2]-bbox[0]) + 2, 44), ".", font=f_brand_big, fill=(255, 106, 26))
    draw.text((90, 66), "SKYDIVE BOOKING TICKET", font=f_brand_sub, fill=(152, 160, 179))

    # ---- CONFIRMED status pill (top-right) ----
    pill_x, pill_y, pill_w, pill_h = 720, 36, 124, 28
    draw.rounded_rectangle((pill_x, pill_y, pill_x+pill_w, pill_y+pill_h),
                           radius=14, outline=(34, 197, 94), width=1,
                           fill=(20, 50, 30))
    draw.ellipse((pill_x+10-4, pill_y+14-4, pill_x+10+4, pill_y+14+4), fill=(34, 197, 94))
    f_pill = _pil_font(11, bold=True)
    draw.text((pill_x+24, pill_y+9), "CONFIRMED", font=f_pill, fill=(74, 222, 128))

    # Perforation divider
    for y in range(100, 320, 10):
        draw.line((240, y, 240, y+4), fill=(31, 39, 55), width=1)

    # ---- LEFT column ----
    f_label = _pil_font(10, bold=True)
    f_h1 = _pil_font(22, bold=True)
    f_h2 = _pil_font(18, bold=True)
    f_body = _pil_font(12)

    draw.text((36, 130), "JUMPER", font=f_label, fill=(152, 160, 179))
    draw.text((36, 148), jumper_name[:30], font=f_h1, fill=(255, 255, 255))

    draw.text((36, 200), "DROP ZONE", font=f_label, fill=(152, 160, 179))
    draw.text((36, 218), zone[:28], font=f_h2, fill=(255, 255, 255))
    draw.text((36, 240), zone_city[:32], font=f_body, fill=(203, 209, 220))

    draw.text((36, 280), "PACKAGE", font=f_label, fill=(152, 160, 179))
    draw.text((36, 298), pkg_name, font=f_h2, fill=(255, 138, 61))

    # ---- RIGHT column ----
    draw.text((280, 130), "DATE", font=f_label, fill=(152, 160, 179))
    draw.text((280, 148), when, font=f_h1, fill=(255, 255, 255))

    draw.text((280, 200), "TIME", font=f_label, fill=(152, 160, 179))
    draw.text((280, 218), time_, font=f_h1, fill=(255, 138, 61))

    draw.text((280, 280), "GROUP", font=f_label, fill=(152, 160, 179))
    draw.text((280, 298), group_label, font=f_h2, fill=(255, 255, 255))

    # Right-most column
    draw.text((600, 130), "AMOUNT", font=f_label, fill=(152, 160, 179))
    draw.text((600, 148), amount, font=f_h1, fill=(255, 255, 255))

    draw.text((600, 200), "REFERENCE", font=f_label, fill=(152, 160, 179))
    draw.text((600, 218), ref, font=f_h2, fill=(255, 138, 61))

    # Footer
    f_foot = _pil_font(10)
    draw.text((36, 326), f"Present this ticket at the drop zone on arrival. Issued {issued}.",
              font=f_foot, fill=(107, 114, 128))
    draw.text((W-36, 326), "skyeman.com", font=f_foot, fill=(107, 114, 128), anchor="rt")

    # Encode
    from io import BytesIO
    buf = BytesIO()
    if fmt == "jpg" or fmt == "jpeg":
        # JPEG doesn't support alpha — flatten onto solid bg (already RGB, fine)
        img.save(buf, format="JPEG", quality=92, optimize=True)
        resp = HttpResponse(buf.getvalue(), content_type="image/jpeg")
        resp["Content-Disposition"] = f'attachment; filename="skyeman-ticket-{ref}.jpg"'
    else:
        img.save(buf, format="PNG", optimize=True)
        resp = HttpResponse(buf.getvalue(), content_type="image/png")
        resp["Content-Disposition"] = f'attachment; filename="skyeman-ticket-{ref}.png"'
    return resp


def _pil_font(size, bold=False):
    """Try a few common font paths so the ticket renders identically on macOS/Linux/Windows."""
    from PIL import ImageFont
    candidates = []
    if bold:
        candidates += [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
        ]
    candidates += [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _build_ticket_svg(jumper_name, zone, zone_city, pkg_name, when, time_,
                      amount, ref, issued, group_label):
    """Build the SVG version of the ticket (kept for users who explicitly request ?format=svg)."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 360" width="880" height="360">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0b0f17"/>
      <stop offset="100%" stop-color="#141a26"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ff6a1a"/>
      <stop offset="100%" stop-color="#ff8a3d"/>
    </linearGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="dots" x="0" y="0" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="#232d3f"/>
    </pattern>
  </defs>
  <rect x="0" y="0" width="880" height="360" rx="20" fill="url(#bg)"/>
  <rect x="0" y="0" width="880" height="360" rx="20" fill="url(#dots)" opacity="0.4"/>
  <rect x="6" y="6" width="868" height="348" rx="18" fill="none" stroke="#1f2737" stroke-width="2"/>
  <rect x="0" y="0" width="6" height="360" rx="3" fill="url(#accent)"/>
  <g transform="translate(36, 36)">
    <circle cx="18" cy="18" r="18" fill="#ff6a1a" filter="url(#glow)"/>
    <path d="M18 6 L21 14 L29 14 L23 19 L25 27 L18 23 L11 27 L13 19 L7 14 L15 14 Z" fill="#fff" opacity="0.95"/>
    <text x="48" y="16" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="800" fill="#ffffff">skyeman</text>
    <text x="155" y="16" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="800" fill="#ff6a1a">.</text>
    <text x="48" y="36" font-family="Inter, system-ui, sans-serif" font-size="10" letter-spacing="2" fill="#98a0b3">SKYDIVE BOOKING TICKET</text>
  </g>
  <g transform="translate(720, 36)">
    <rect x="0" y="0" width="120" height="28" rx="14" fill="rgba(34,197,94,0.15)" stroke="#22c55e" stroke-width="1"/>
    <circle cx="14" cy="14" r="4" fill="#22c55e"/>
    <text x="26" y="18" font-family="Inter, system-ui, sans-serif" font-size="11" font-weight="700" fill="#4ade80" letter-spacing="1.5">CONFIRMED</text>
  </g>
  <line x1="240" y1="100" x2="240" y2="320" stroke="#1f2737" stroke-width="1" stroke-dasharray="4 6"/>
  <g transform="translate(36, 130)" font-family="Inter, system-ui, sans-serif">
    <text x="0" y="0" font-size="10" letter-spacing="2" fill="#98a0b3">JUMPER</text>
    <text x="0" y="28" font-size="22" font-weight="700" fill="#ffffff">{jumper_name}</text>
    <text x="0" y="74" font-size="10" letter-spacing="2" fill="#98a0b3">DROP ZONE</text>
    <text x="0" y="98" font-size="18" font-weight="700" fill="#ffffff">{zone}</text>
    <text x="0" y="118" font-size="12" fill="#cbd1dc">{zone_city}</text>
    <text x="0" y="158" font-size="10" letter-spacing="2" fill="#98a0b3">PACKAGE</text>
    <text x="0" y="180" font-size="18" font-weight="700" fill="#ff8a3d">{pkg_name}</text>
  </g>
  <g transform="translate(280, 130)" font-family="Inter, system-ui, sans-serif">
    <text x="0" y="0" font-size="10" letter-spacing="2" fill="#98a0b3">DATE</text>
    <text x="0" y="28" font-size="22" font-weight="800" fill="#ffffff">{when}</text>
    <text x="0" y="74" font-size="10" letter-spacing="2" fill="#98a0b3">TIME</text>
    <text x="0" y="98" font-size="22" font-weight="800" fill="#ff8a3d">{time_}</text>
    <text x="0" y="148" font-size="10" letter-spacing="2" fill="#98a0b3">GROUP</text>
    <text x="0" y="170" font-size="18" font-weight="700" fill="#ffffff">{group_label}</text>
    <text x="280" y="0" font-size="10" letter-spacing="2" fill="#98a0b3">AMOUNT</text>
    <text x="280" y="28" font-size="22" font-weight="800" fill="#ffffff">{amount}</text>
    <text x="280" y="74" font-size="10" letter-spacing="2" fill="#98a0b3">REFERENCE</text>
    <text x="280" y="98" font-size="16" font-weight="700" fill="#ff8a3d">{ref}</text>
  </g>
  <g transform="translate(36, 312)" font-family="Inter, system-ui, sans-serif">
    <text x="0" y="14" font-size="10" fill="#6b7280">Present this ticket at the drop zone on arrival. Issued {issued}.</text>
  </g>
  <text x="844" y="328" text-anchor="end" font-family="Inter, system-ui, sans-serif" font-size="10" fill="#6b7280">skyeman.com</text>
</svg>'''
