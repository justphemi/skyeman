"""Seed the database with drop zones, jump packages, an admin user, and demo slots.

Customer users, bookings, and payments are NOT seeded — customers sign up
at /accounts/signup/ and admins create bookings via /admin/ or /manage/.

Usage:
    python manage.py seed
    python manage.py seed --reset
"""
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from django.contrib.auth.models import User

from dropzones.models import DropZone, JumpPackage, TimeSlot


ADMIN_EMAIL = "admin@skyeman.com"
ADMIN_PASSWORD = "Skyeman123!"


class Command(BaseCommand):
    help = "Populate the database with drop zones and jump packages."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Drop existing drop zones and packages before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        from bookings.models import Booking, Payment, BookingParticipant

        if opts["reset"]:
            self.stdout.write(self.style.WARNING("Resetting drop zones and packages…"))
            # Clean dependent records first (Bookings PROTECT both DropZone and TimeSlot,
            # and TimeSlots PROTECT DropZone). The seed is a clean slate — wipe everything
            # except users.
            BookingParticipant.objects.all().delete()
            Payment.objects.all().delete()
            Booking.objects.all().delete()
            TimeSlot.objects.all().delete()
            DropZone.objects.all().delete()
            JumpPackage.objects.all().delete()

        zones_data = [
            {
                "name": "Ikoyi Airfield",
                "city": "Ikoyi, Lagos",
                "address": "14 Alexander Avenue, Ikoyi, Lagos",
                "description": "Lagos Island's skydive hub. Scenic views of the Lagos Lagoon, the Third Mainland Bridge, and the Atlantic coastline beyond.",
                "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS8UoDelWXrCbALjub11t6BjCSfApzMnNWEeqXtFIhpNA&s=10",
            },
            {
                "name": "Lekki Coastal",
                "city": "Lekki, Lagos",
                "address": "Km 18, Lekki–Epe Expressway, Lekki Phase 1, Lagos",
                "description": "Beachside tandem jumps over the Lekki coastline. Year-round warm weather, gentle Atlantic breezes, and ocean sunsets from 12,000 feet.",
                "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRJMKL7ZIjG9OaVfSK2EgVtLxONLC1f3OxtvdYNJslhCA&s=10",
            },
            {
                "name": "Victoria Island Skyport",
                "city": "Victoria Island, Lagos",
                "address": "Plot 24, Akin Adesola Street, Victoria Island, Lagos",
                "description": "Our urban jump center minutes from Eko Atlantic. Features ultra-fast turbine aircraft, modern ground simulation trainers, and panoramic views of the city skyline.",
                "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTn84ue-pHOZzFs345mK2lRI7q6vcpmfM_18Kvv3C71kA&s=10",
            },
        ]
        dropzones = []
        for zd in zones_data:
            dz, _ = DropZone.objects.get_or_create(name=zd["name"], defaults=zd)
            for k, v in zd.items():
                setattr(dz, k, v)
            dz.save()
            dropzones.append(dz)
        self.stdout.write(self.style.SUCCESS(f"✓ {len(dropzones)} Drop Zones loaded"))

        packages_data = [
            ("Tandem", "120000.00", "First-time thrill. Securely harnessed to a certified instructor from 12,000 feet with 45 seconds of freefall and a gentle 5-minute canopy ride.", 18, 100, 20),
            ("AFF", "220000.00", "Accelerated Freefall ground school and Level 1 solo progression. Jump with your own parachute alongside two instructors holding your grips.", 18, 95, 240),
            ("Solo", "55000.00", "For licensed skydivers (USPA A-license or equivalent). Full rig rental, altimeter, packing service, and lift ticket to 14,000 ft.", 18, 100, 20),
            ("Group", "95000.00", "Special rate for teams of 4+ jumpers. Includes a personal instructor for each jumper, group briefing, and complimentary celebratory toast.", 16, 110, 30),
        ]
        packages = []
        for name, price, desc, min_age, max_w, dur in packages_data:
            pkg, _ = JumpPackage.objects.get_or_create(
                name=name,
                defaults={
                    "price": Decimal(price),
                    "description": desc,
                    "min_age": min_age,
                    "max_weight_kg": max_w,
                    "duration_minutes": dur,
                },
            )
            pkg.price = Decimal(price)
            pkg.description = desc
            pkg.min_age = min_age
            pkg.max_weight_kg = max_w
            pkg.duration_minutes = dur
            pkg.save()
            packages.append(pkg)
        self.stdout.write(self.style.SUCCESS(f"✓ {len(packages)} Jump Packages configured"))

        # Admin user (idempotent: refresh password + flags every run so credentials are always usable).
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": ADMIN_EMAIL,
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Skyeman",
                "last_name": "Admin",
            },
        )
        admin.email = ADMIN_EMAIL
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(ADMIN_PASSWORD)
        admin.save()
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"✓ Admin user {verb}: email={ADMIN_EMAIL} password={ADMIN_PASSWORD}"
        ))

        # Demo time slots: 4 future slots spread across drop zones / dates.
        # Slot #2 has capacity=1 — when one user books it, it must auto-flip to full
        # (TimeSlot.update_status runs after every booking) so no other user can grab it.
        today = date.today()
        demo_slots = [
            # (drop_zone_name, offset_days, start_hour, start_minute, capacity)
            ("Ikoyi Airfield",            1, 9, 0, 8),
            ("Lekki Coastal",              2, 10, 0, 1),   # capacity 1 — single-seat demo
            ("Victoria Island Skyport",   3, 11, 0, 8),
            ("Ikoyi Airfield",             5, 14, 0, 6),
        ]
        slot_count = 0
        for dz_name, offset, hh, mm, cap in demo_slots:
            try:
                dz = DropZone.objects.get(name=dz_name)
            except DropZone.DoesNotExist:
                continue
            slot_date = today + timedelta(days=offset)
            slot_time = time(hh, mm)
            slot, s_created = TimeSlot.objects.get_or_create(
                drop_zone=dz,
                date=slot_date,
                start_time=slot_time,
                defaults={"capacity": cap, "status": "open"},
            )
            # Refresh capacity on every seed run so the demo is always in the expected state.
            slot.capacity = cap
            if slot.status == "cancelled":
                slot.status = "open"
            slot.save()
            slot_count += 1
        self.stdout.write(self.style.SUCCESS(f"✓ {slot_count} Demo Time Slots loaded"))

        self.stdout.write(self.style.SUCCESS("\n=========================================="))
        self.stdout.write(self.style.SUCCESS("✓ SKYEMAN SEED COMPLETED"))
        self.stdout.write(self.style.SUCCESS("  Drop zones:    3"))
        self.stdout.write(self.style.SUCCESS("  Jump packages: 4"))
        self.stdout.write(self.style.SUCCESS(f"  Demo slots:    {slot_count} (incl. 1 capacity=1 slot that auto-fills)"))
        self.stdout.write(self.style.SUCCESS(f"  Admin user:    {ADMIN_EMAIL} / {ADMIN_PASSWORD}"))
        self.stdout.write(self.style.SUCCESS("=========================================="))
