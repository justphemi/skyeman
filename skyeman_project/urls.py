"""Skyeman Inc. - top-level URL configuration.
Routes traffic to the right app or the admin.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .health import healthz

urlpatterns = [
    # Health check for uptime monitors (Render, load balancers, etc.)
    path("healthz/", healthz, name="healthz"),

    # Django admin (customised in each app's admin.py)
    path("admin/", admin.site.urls),

    # Customer-facing apps
    path("", include(("dropzones.urls", "dropzones"), namespace="dropzones")),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("bookings/", include(("bookings.urls", "bookings"), namespace="bookings")),

    # Operations console (staff-only friendly UI, separate from Django admin)
    path("manage/", include(("manage_ui.urls", "manage_ui"), namespace="manage_ui")),
]

# Serve static and media in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
