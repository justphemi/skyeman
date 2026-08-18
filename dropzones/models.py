"""Dropzones app — models for DropZone, JumpPackage, and TimeSlot.

There is a single instructor: Femi. We don't model instructor records anymore —
the name is referenced as a constant in templates where appropriate.
"""
from datetime import datetime
from django.db import models
from django.utils import timezone


INSTRUCTOR_NAME = "Femi"


class DropZone(models.Model):
    """A physical skydiving location (airfield + landing zone)."""
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=80)
    address = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True, help_text="Optional cover image URL for this drop zone")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.city})"

    @property
    def upcoming_slots_count(self):
        return self.time_slots.filter(date__gte=timezone.now().date(), status="open").count()


class JumpPackage(models.Model):
    """A skydive offering (Tandem, AFF, Solo, Group) with eligibility and price in Naira."""
    PACKAGE_CHOICES = [
        ("Tandem", "Tandem"),
        ("AFF", "AFF (Accelerated Freefall)"),
        ("Solo", "Solo"),
        ("Group", "Group"),
    ]
    name = models.CharField(max_length=20, choices=PACKAGE_CHOICES, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField()
    min_age = models.PositiveSmallIntegerField(default=18)
    max_weight_kg = models.PositiveSmallIntegerField(default=100)
    duration_minutes = models.PositiveSmallIntegerField(default=20)
    image_url = models.URLField(blank=True, help_text="Optional cover image URL")

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} — ₦{self.price:,.0f}"


class TimeSlot(models.Model):
    """A scheduled jump session at a specific drop zone, date, and time."""
    STATUS_CHOICES = [
        ("open", "Open"),
        ("full", "Full"),
        ("cancelled", "Cancelled (Weather)"),
    ]
    drop_zone = models.ForeignKey(DropZone, on_delete=models.CASCADE, related_name="time_slots")
    date = models.DateField()
    start_time = models.TimeField()
    capacity = models.PositiveSmallIntegerField(default=8)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="open")

    class Meta:
        ordering = ["date", "start_time"]
        unique_together = [("drop_zone", "date", "start_time")]

    def __str__(self):
        return f"{self.drop_zone.name} — {self.date.strftime('%b %d, %Y')} @ {self.start_time.strftime('%I:%M %p')}"

    @property
    def booked_count(self):
        """Number of active (non-cancelled) bookings for this slot."""
        return self.bookings.exclude(status="cancelled").count()

    @property
    def seats_left(self):
        """Remaining seats for this time slot."""
        return max(0, self.capacity - self.booked_count)

    @property
    def is_available(self):
        """Check if slot is in the future, open, and has open capacity."""
        if self.status != "open" or self.seats_left <= 0:
            return False
        slot_dt = datetime.combine(self.date, self.start_time)
        if timezone.is_naive(slot_dt):
            slot_dt = timezone.make_aware(slot_dt, timezone.get_current_timezone())
        return slot_dt > timezone.now()

    def update_status(self):
        """Auto-update status based on booked count and capacity."""
        if self.booked_count >= self.capacity:
            if self.status != "full":
                self.status = "full"
                self.save(update_fields=["status"])
        elif self.status == "full" and self.booked_count < self.capacity:
            self.status = "open"
            self.save(update_fields=["status"])
        return self.status
