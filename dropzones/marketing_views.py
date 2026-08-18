"""Marketing pages for the dropzones app."""
from django.shortcuts import render
from .models import DropZone


def about(request):
    return render(request, "marketing/about.html")


def how_it_works(request):
    return render(request, "marketing/how_it_works.html")


def faq(request):
    return render(request, "marketing/faq.html")


def contact(request):
    drop_zones = DropZone.objects.all()
    return render(request, "marketing/contact.html", {"drop_zones": drop_zones})