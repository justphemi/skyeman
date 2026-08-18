from datetime import date, time, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from dropzones.models import DropZone, JumpPackage, TimeSlot
from bookings.models import Booking, Payment


class SkyemanBookingFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testjumper",
            email="test@skyeman.ng",
            password="testpassword123",
            first_name="Test",
            last_name="Jumper",
        )
        self.admin = User.objects.create_superuser(
            username="testadmin",
            email="admin@skyeman.ng",
            password="adminpassword123",
            is_staff=True,
            is_superuser=True,
        )
        self.drop_zone = DropZone.objects.create(
            name="Lekki Beach DZ",
            city="Lagos",
            address="Coastal Road, Lekki Phase 1",
            description="Oceanfront dropzone",
        )
        self.pkg = JumpPackage.objects.create(
            name="Tandem",
            price=120000,
            duration_minutes=20,
            min_age=18,
            max_weight_kg=100,
            description="First jump over Lagos Atlantic coast",
        )
        self.slot = TimeSlot.objects.create(
            drop_zone=self.drop_zone,
            date=date.today() + timedelta(days=2),
            start_time=time(10, 0),
            capacity=4,
            status="open",
        )

    def test_homepage_loads(self):
        response = self.client.get(reverse("dropzones:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skyeman")

    def test_timeslot_list_loads(self):
        response = self.client.get(reverse("dropzones:timeslot_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lekki Beach DZ")

    def test_booking_creation_and_payment_flow(self):
        self.client.login(username="testjumper", password="testpassword123")
        
        # Step 1: Create booking
        create_url = reverse("bookings:create")
        post_data = {
            "time_slot": self.slot.pk,
            "package": self.pkg.pk,
            "jumper_age": 25,
            "jumper_weight_kg": 75,
            "notes": "First jump, excited!",
        }
        res = self.client.post(create_url, post_data)
        self.assertEqual(res.status_code, 302)
        
        # Verify booking exists
        booking = Booking.objects.filter(user=self.user).first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, "pending")
        
        # Step 2: Pay for booking
        pay_url = reverse("bookings:pay", kwargs={"pk": booking.pk})
        pay_data = {
            "method": "card",
            "card_name": "Test Jumper",
            "card_number": "4242 4242 4242 4242",
            "card_expiry": "12/28",
            "card_cvv": "888",
        }
        pay_res = self.client.post(pay_url, pay_data)
        self.assertEqual(pay_res.status_code, 302)
        
        # Reload booking and check status & payment
        booking.refresh_from_db()
        self.assertEqual(booking.status, "confirmed")
        self.assertIsNotNone(booking.payment)
        self.assertEqual(booking.payment.status, "paid")

    def test_custom_admin_dashboard_loads_for_staff(self):
        self.client.login(username="testadmin", password="adminpassword123")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operations dashboard")
