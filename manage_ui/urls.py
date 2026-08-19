from django.urls import path

from . import views

app_name = "manage_ui"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("bookings/", views.bookings_list, name="bookings"),
    path("bookings/<int:pk>/", views.booking_detail, name="booking_detail"),
    path("bookings/<int:pk>/action/", views.booking_action, name="booking_action"),
    path("dropzones/", views.dropzones_list, name="dropzones"),
    path("users/", views.users_list, name="users"),
    path("payments/", views.payments_list, name="payments"),
    path("slots/", views.slots_list, name="slots"),
    path("slots/new/", views.slot_create, name="slot_create"),
    path("slots/<int:pk>/action/", views.slot_action, name="slot_action"),
]
