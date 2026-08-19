"""URL routing for the bookings app."""
from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.my_bookings, name="my_bookings"),
    path("book/", views.booking_step_dropzone, name="create"),
    path("book/step-1/", views.booking_step_dropzone, name="step_dropzone"),
    path("book/step-2/", views.booking_step_package, name="step_package"),
    path("book/step-3/", views.booking_step_slot, name="step_slot"),
    path("book/step-4/", views.booking_step_details, name="step_details"),
    path("<int:pk>/", views.booking_detail, name="detail"),
    path("<int:pk>/pay/", views.booking_pay, name="pay"),
    path("<int:pk>/confirmation/", views.booking_confirmation, name="confirmation"),
    path("<int:pk>/reschedule/", views.booking_reschedule, name="reschedule"),
    path("<int:pk>/cancel/", views.booking_cancel, name="cancel"),
    path("<int:pk>/ticket", views.booking_ticket_svg, name="ticket"),
]
