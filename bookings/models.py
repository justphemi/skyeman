"""Bookings app — Booking and Payment models.

A Booking ties a User to a TimeSlot and a JumpPackage.
Each Booking has at most one Payment (one-to-one).
A Booking may have multiple BookingParticipant entries (group jump).
Payment is a simulated checkout.
"""
from datetime import datetime
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils import timezone

from dropzones.models import TimeSlot, JumpPackage


class Booking(models.Model):
    """A customer reservation of a specific TimeSlot with a selected JumpPackage."""
    STATUS_CHOICES = [
        ("pending", "Pending payment"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT, related_name="bookings")
    package = models.ForeignKey(JumpPackage, on_delete=models.PROTECT, related_name="bookings")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(default=timezone.now)
    jumper_age = models.PositiveSmallIntegerField(null=True, blank=True)
    jumper_weight_kg = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    group_size = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of jumpers in this booking (1 for solo, 2+ for group packages).",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Booking #{self.pk} — {self.user.username} @ {self.time_slot}"

    @property
    def total_price(self):
        """Total price the user pays: per-person × group size, with optional group discount."""
        per_person = self.package.price
        size = max(1, self.group_size or 1)
        if self.package.name == "Group" and size >= 3:
            # 10% group discount for 3+ jumpers
            return per_person * size * Decimal("0.9")
        return per_person * size

    @property
    def is_cancellable(self):
        """A booking can be cancelled while its slot is in the future and status is pending or confirmed."""
        slot_dt = datetime.combine(self.time_slot.date, self.time_slot.start_time)
        if timezone.is_naive(slot_dt):
            slot_dt = timezone.make_aware(slot_dt, timezone.get_current_timezone())
        return slot_dt > timezone.now() and self.status in ("pending", "confirmed")

    @property
    def is_reschedulable(self):
        """A booking can be rescheduled if it is active and in the future."""
        return self.is_cancellable


class BookingParticipant(models.Model):
    """A single jumper in a (potentially group) booking. Captures name, age, weight."""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="participants")
    full_name = models.CharField(max_length=120)
    age = models.PositiveSmallIntegerField()
    weight_kg = models.PositiveSmallIntegerField(null=True, blank=True)
    is_lead = models.BooleanField(
        default=False,
        help_text="True if this participant is the lead jumper / booker.",
    )

    class Meta:
        ordering = ["is_lead", "id"]

    def __str__(self):
        role = "Lead" if self.is_lead else "Companion"
        return f"{role}: {self.full_name} ({self.age})"


class Payment(models.Model):
    """Simulated payment for a booking."""
    METHOD_CHOICES = [
        ("card", "Credit / Debit Card (simulated)"),
        ("paypal", "PayPal (simulated)"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
        ("failed", "Failed"),
    ]
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default="card")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment #{self.pk} for Booking #{self.booking_id} — {self.get_status_display()} (₦{self.amount:,.0f})"
