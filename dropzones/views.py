"""Dropzones app — customer-facing views."""
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.db.models import Count

from .models import DropZone, JumpPackage, TimeSlot, INSTRUCTOR_NAME


def home(request):
    """Landing page — hero, stats, featured drop zones, jump package highlights, testimonials."""
    drop_zones = DropZone.objects.prefetch_related("time_slots").all()[:3]
    packages = JumpPackage.objects.all()[:4]
    upcoming_slots = (
        TimeSlot.objects.filter(date__gte=date.today(), status="open")
        .select_related("drop_zone")
        .order_by("date", "start_time")[:6]
    )
    total_dropzones = DropZone.objects.count()

    return render(request, "dropzones/home.html", {
        "drop_zones": drop_zones,
        "packages": packages,
        "upcoming_slots": upcoming_slots,
        "total_dropzones": total_dropzones,
        "instructor_name": INSTRUCTOR_NAME,
    })


class DropZoneListView(ListView):
    """All drop zones as a modern responsive card grid."""
    model = DropZone
    template_name = "dropzones/dropzone_list.html"
    context_object_name = "drop_zones"

    def get_queryset(self):
        return DropZone.objects.prefetch_related("time_slots").all()


class DropZoneDetailView(DetailView):
    """Detail page for a drop zone: description and upcoming available slots."""
    model = DropZone
    template_name = "dropzones/dropzone_detail.html"
    context_object_name = "drop_zone"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slots"] = (
            self.object.time_slots
            .filter(date__gte=date.today())
            .order_by("date", "start_time")
        )
        ctx["packages"] = JumpPackage.objects.all()
        ctx["instructor_name"] = INSTRUCTOR_NAME
        return ctx


class PackageListView(ListView):
    """All skydiving packages as a card grid with pricing in Naira and eligibility requirements."""
    model = JumpPackage
    template_name = "dropzones/package_list.html"
    context_object_name = "packages"


class TimeSlotListView(ListView):
    """All upcoming available jump slots across all drop zones, with drop zone and date filters."""
    model = TimeSlot
    template_name = "dropzones/timeslot_list.html"
    context_object_name = "slots"
    paginate_by = 12

    def get_queryset(self):
        qs = (
            TimeSlot.objects
            .filter(date__gte=date.today())
            .select_related("drop_zone")
            .order_by("date", "start_time")
        )
        dz_id = self.request.GET.get("dropzone")
        if dz_id and dz_id.isdigit():
            qs = qs.filter(drop_zone_id=int(dz_id))
        
        status_filter = self.request.GET.get("status")
        if status_filter in ["open", "full", "cancelled"]:
            qs = qs.filter(status=status_filter)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["drop_zones"] = DropZone.objects.all()
        ctx["selected_dz"] = self.request.GET.get("dropzone", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["packages"] = JumpPackage.objects.all()
        return ctx


# Marketing & information pages
def about(request):
    return render(request, "marketing/about.html")


def how_it_works(request):
    packages = JumpPackage.objects.all()
    return render(request, "marketing/how_it_works.html", {"packages": packages})


def faq(request):
    return render(request, "marketing/faq.html")


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "Friend")
        messages.success(request, f"Thanks {name}! We received your message and will reply within 24 hours.")
        return redirect("dropzones:contact")
    return render(request, "marketing/contact.html")


def gallery(request):
    return render(request, "dropzones/gallery.html")


def blog(request):
    return render(request, "marketing/blog.html")


def careers(request):
    return render(request, "marketing/careers.html")


def newsletter(request):
    if request.method == "POST":
        email = request.POST.get("email", "")
        if email:
            messages.success(request, f"Thanks for subscribing! The Skyeman Dispatch has been sent to {email}.")
        else:
            messages.info(request, "Please enter a valid email address.")
        return redirect("dropzones:newsletter")
    return render(request, "marketing/newsletter.html")


def privacy(request):
    return render(request, "marketing/privacy.html")


def terms(request):
    return render(request, "marketing/terms.html")


def cookies(request):
    return render(request, "marketing/cookies.html")
