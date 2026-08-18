"""URL routing for the dropzones app."""
from django.urls import path
from . import views

app_name = "dropzones"

urlpatterns = [
    # Main booking & location pages
    path("", views.home, name="home"),
    path("zones/", views.DropZoneListView.as_view(), name="dropzone_list"),
    path("zones/<int:pk>/", views.DropZoneDetailView.as_view(), name="dropzone_detail"),
    path("packages/", views.PackageListView.as_view(), name="package_list"),
    path("slots/", views.TimeSlotListView.as_view(), name="timeslot_list"),

    # Marketing & info pages
    path("about/", views.about, name="about"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("gallery/", views.gallery, name="gallery"),
    path("blog/", views.blog, name="blog"),
    path("careers/", views.careers, name="careers"),
    path("newsletter/", views.newsletter, name="newsletter"),

    # Legal pages
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("cookies/", views.cookies, name="cookies"),
]
