"""Seed the database with drop zones and jump packages only.

Time slots, users, instructors, bookings, and payments are NOT seeded —
the admin sets those up via /admin/ and /manage/.

Usage:
    python manage.py seed
    python manage.py seed --reset
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from dropzones.models import DropZone, JumpPackage


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
        if opts["reset"]:
            self.stdout.write(self.style.WARNING("Resetting drop zones and packages…"))
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

        self.stdout.write(self.style.SUCCESS("\n=========================================="))
        self.stdout.write(self.style.SUCCESS("✓ SKYEMAN SEED COMPLETED"))
        self.stdout.write(self.style.SUCCESS("  Drop zones:    3"))
        self.stdout.write(self.style.SUCCESS("  Jump packages: 4"))
        self.stdout.write(self.style.SUCCESS("  Time slots:    0 (admin sets these via /manage/slots/)"))
        self.stdout.write(self.style.SUCCESS("  Users:         0 (sign up yourself at /accounts/signup/)"))
        self.stdout.write(self.style.SUCCESS("=========================================="))
