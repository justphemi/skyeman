"""URL routing for the accounts app."""
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("login/", views.SkyemanLoginView.as_view(), name="login"),
    path("logout/", views.SkyemanLogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="profile_edit"),
]
