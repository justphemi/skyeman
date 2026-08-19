"""Accounts app — sign up, log in, log out, user dashboard, and profile management."""
from datetime import date
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import SignUpForm, ProfileForm, EmailAuthenticationForm


class SignUpView(CreateView):
    """Customer sign-up. Logs the user in on success and routes to dashboard."""
    form_class = SignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:dashboard")

    def form_valid(self, form):
        # Let CreateView.form_valid save the user first (so self.object is set,
        # the user has a pk, and the password is hashed exactly once).
        response = super().form_valid(form)
        # IMPORTANT: login() must happen AFTER super().form_valid() because that's
        # where the user is persisted to the DB. The response from super() is
        # an HttpResponseRedirect — Django's session middleware will still attach
        # the session cookie to that response (login() modifies request.session
        # which the middleware reads when building the response).
        login(self.request, self.object)
        messages.success(self.request, f"Welcome to Skyeman, {self.object.first_name or self.object.username}!")
        return response


class SkyemanLoginView(LoginView):
    """Branded login view supporting username or email login."""
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    # NOTE: do NOT set redirect_authenticated_user=True — LOGIN_REDIRECT_URL points
    # to /accounts/dashboard/ which is @login_required, creating an infinite loop
    # (login → dashboard → login → dashboard) for already-authenticated users who
    # somehow end up on /login/. Leave the default False: an already-logged-in user
    # just sees the login form (with a friendly notice in the template).

    def form_valid(self, form):
        user = form.get_user()
        messages.success(self.request, f"Welcome back, {user.first_name or user.username}!")
        return super().form_valid(form)


class SkyemanLogoutView(LogoutView):
    """Safe logout view redirecting to homepage with notice."""
    next_page = reverse_lazy("dropzones:home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You have been logged out safely. See you in the sky!")
        return super().dispatch(request, *args, **kwargs)


@login_required
def dashboard(request):
    """Customer command center: stats, upcoming jumps, recent bookings, and profile quick-actions."""
    from bookings.models import Booking

    bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related("time_slot__drop_zone", "package", "payment")
        .order_by("-created_at")
    )

    confirmed_count = bookings.filter(status="confirmed").count()
    completed_count = bookings.filter(status="completed").count()
    pending_count = bookings.filter(status="pending").count()
    total_jumps = confirmed_count + completed_count

    upcoming_bookings = [
        b for b in bookings if b.status in ("pending", "confirmed") and b.time_slot.date >= date.today()
    ]

    member_since = request.user.date_joined.strftime("%B %Y") if request.user.date_joined else "2026"

    return render(request, "accounts/dashboard.html", {
        "bookings": bookings,
        "upcoming_bookings": upcoming_bookings,
        "confirmed_count": confirmed_count,
        "completed_count": completed_count,
        "pending_count": pending_count,
        "total_jumps": total_jumps,
        "member_since": member_since,
    })


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Allows customers to update their name and email."""
    form_class = ProfileForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:dashboard")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been updated.")
        return super().form_valid(form)
