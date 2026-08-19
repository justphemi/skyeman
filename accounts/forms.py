"""Accounts app — forms for sign up, log in (email/username + password), and profile editing."""
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


class EmailAuthenticationForm(AuthenticationForm):
    """Log in with email or username + password."""
    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email or Username"
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        raw_username = self.cleaned_data.get("username", "").strip()
        password = self.cleaned_data.get("password")
        if raw_username and password:
            # Check if raw_username is an email
            if "@" in raw_username:
                user_obj = User.objects.filter(email__iexact=raw_username).first()
                if user_obj:
                    self.cleaned_data["username"] = user_obj.username
            else:
                user_obj = User.objects.filter(username__iexact=raw_username).first()
                if user_obj:
                    self.cleaned_data["username"] = user_obj.username
        return super().clean()


class SignUpForm(UserCreationForm):
    """Sign-up form: email, optional full name, and password (single field, no confirm)."""
    full_name = forms.CharField(
        max_length=160,
        required=False,
        label="Full name",
        help_text="Your first and last name.",
    )
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        # Single password field — we dropped password2 (the confirm field) per UX request.
        fields = ("username", "full_name", "email", "password1")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Drop the confirm-password field — single password field is the UX we want.
        # UserCreationForm still declares password2 on `self.fields`; remove it before validation.
        if "password2" in self.fields:
            del self.fields["password2"]
        self.fields["username"].required = False
        self.fields["username"].widget = forms.HiddenInput()
        self.fields["username"].help_text = ""
        if not self.initial.get("username"):
            self.fields["username"].initial = "user"
        for name, f in self.fields.items():
            if name != "username":
                f.widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        full_name = cleaned.get("full_name", "").strip()
        email = cleaned.get("email", "").strip()

        if full_name:
            parts = full_name.split(maxsplit=1)
            cleaned["first_name"] = parts[0]
            cleaned["last_name"] = parts[1] if len(parts) > 1 else ""
        elif email:
            base_name = email.split("@")[0].replace(".", " ").title()
            parts = base_name.split(maxsplit=1)
            cleaned["first_name"] = parts[0]
            cleaned["last_name"] = parts[1] if len(parts) > 1 else ""

        # Generate unique username
        base = email.split("@")[0] if "@" in email else (full_name.replace(" ", "").lower() or "jumper")
        base = base or "jumper"
        username = base
        n = 1
        while User.objects.filter(username__iexact=username).exists():
            n += 1
            username = f"{base}{n}"
        cleaned["username"] = username
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.email = self.cleaned_data.get("email", "")
        user.username = self.cleaned_data["username"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Edit first name / last name / email from the dashboard."""
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")
