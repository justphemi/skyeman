"""Bookings app — forms for booking creation, rescheduling, and simulated payment."""
from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Booking
from dropzones.models import TimeSlot, JumpPackage


class BookingParticipantForm(forms.Form):
    """One companion jumper row (name + age + optional weight)."""
    full_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Companion full name"}),
        label="Full name",
    )
    age = forms.IntegerField(
        min_value=16,
        max_value=100,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Age"}),
        label="Age",
    )
    weight_kg = forms.IntegerField(
        required=False,
        min_value=30,
        max_value=150,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Weight (kg, optional)"}),
        label="Weight (kg)",
    )


class BookingDetailsForm(forms.ModelForm):
    """Step 4: jumper details for the booking wizard."""
    jumper_age = forms.IntegerField(
        min_value=16,
        max_value=100,
        initial=25,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g., 25"}),
        label="Your Age (Years)",
    )
    jumper_weight_kg = forms.IntegerField(
        min_value=30,
        max_value=150,
        initial=75,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g., 75"}),
        label="Your Weight (kg)",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "First time jumping? Medical considerations, shoutouts, or special requests?",
        }),
        label="Notes / Special Requests",
    )
    group_size = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "min": "1",
            "max": "10",
        }),
        label="How many jumpers total? (you + friends)",
    )

    class Meta:
        model = Booking
        fields = ("group_size", "jumper_age", "jumper_weight_kg", "notes")

    def __init__(self, *args, **kwargs):
        self._package = kwargs.pop("package", None)
        self._slot = kwargs.pop("slot", None)
        super().__init__(*args, **kwargs)
        self.companion_forms = []
        for i in range(9):
            cf = BookingParticipantForm(self.data if self.data else None, prefix=f"companion_{i}")
            self.companion_forms.append(cf)

    def get_companion_forms(self):
        return self.companion_forms

    def clean(self):
        cleaned = super().clean()
        package = self._package or cleaned.get("package")
        slot = self._slot
        age = cleaned.get("jumper_age")
        weight = cleaned.get("jumper_weight_kg")
        group_size = cleaned.get("group_size") or 1

        if slot and slot.seats_left < group_size:
            raise ValidationError(
                _(f"This slot only has {slot.seats_left} seat(s) left — not enough for a party of {group_size}.")
            )

        if package and age and age < package.min_age:
            raise ValidationError(
                _(f"Minimum age for the {package.name} package is {package.min_age} years old.")
            )

        if package and weight and weight > package.max_weight_kg:
            raise ValidationError(
                _(f"Maximum weight for {package.name} is {package.max_weight_kg} kg for canopy safety.")
            )

        if package and package.name == "Group" and group_size < 2:
            raise ValidationError(
                _("The Group package requires at least 2 jumpers.")
            )

        companions = []
        if group_size > 1:
            needed = group_size - 1
            for i, cf in enumerate(self.companion_forms[:needed]):
                if cf.is_valid():
                    companions.append(cf.cleaned_data)
                else:
                    for field, errs in cf.errors.items():
                        for e in errs:
                            self.add_error(None, f"Companion #{i + 1} ({field}): {e}")
            if len(companions) < needed:
                raise ValidationError(_(f"Please provide the name and age for all {needed} companion(s)."))

        cleaned["_companions"] = companions
        return cleaned


class RescheduleBookingForm(forms.Form):
    """Form to change a booking's time slot."""
    new_time_slot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Select New Available Time Slot",
    )

    def __init__(self, *args, **kwargs):
        current_booking = kwargs.pop("booking", None)
        super().__init__(*args, **kwargs)
        qs = (
            TimeSlot.objects.filter(date__gte=date.today(), status="open")
            .select_related("drop_zone")
            .order_by("date", "start_time")
        )
        if current_booking:
            qs = qs.exclude(id=current_booking.time_slot_id)
        self.fields["new_time_slot"].queryset = qs


class PaymentForm(forms.Form):
    """Simulated payment checkout form."""
    method = forms.ChoiceField(
        choices=[
            ("card", "Credit / Debit Card (Simulated instant checkout)"),
            ("paypal", "PayPal (Simulated sandbox)"),
        ],
        widget=forms.RadioSelect(attrs={"class": "payment-method-radio"}),
        initial="card",
    )
    card_name = forms.CharField(
        required=False,
        initial="Alex Demo",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Cardholder Name"}),
    )
    card_number = forms.CharField(
        required=False,
        initial="4242 •••• •••• 4242",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "4242 4242 4242 4242"}),
    )
    card_expiry = forms.CharField(
        required=False,
        initial="12/28",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "MM/YY"}),
    )
    card_cvv = forms.CharField(
        required=False,
        initial="888",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "CVV"}),
    )
