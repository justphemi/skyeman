"""Bookings app — Django admin customisations.

Includes:
  - list_display / list_filter / search on Booking & Payment
  - Inlines for Payment under Booking
  - Custom admin actions
  - A custom admin operations dashboard at /admin/
"""
from datetime import date, timedelta
from django.contrib import admin
from django.shortcuts import render
from django.db.models import Sum
from django.utils.html import format_html

from .models import Booking, Payment
from dropzones.models import TimeSlot


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = ("paid_at",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "time_slot", "package", "status", "created_at", "total_price_display", "payment_status_display")
    list_filter = ("status", "time_slot__drop_zone", "package", "time_slot__date")
    search_fields = ("user__username", "user__email", "time_slot__drop_zone__name", "notes")
    date_hierarchy = "created_at"
    autocomplete_fields = ("user", "time_slot")
    readonly_fields = ("created_at",)
    inlines = [PaymentInline]
    list_per_page = 25
    actions = ["mark_confirmed", "mark_completed", "mark_cancelled"]

    def total_price_display(self, obj):
        return f"₦{obj.total_price:,.0f}"
    total_price_display.short_description = "Price"

    def payment_status_display(self, obj):
        if hasattr(obj, "payment"):
            color = {
                "paid": "#16a34a",
                "pending": "#f59e0b",
                "refunded": "#8b5cf6",
                "failed": "#dc2626",
            }.get(obj.payment.status, "#9ca3af")
            return format_html(
                '<span style="background:rgba(255,255,255,0.06);padding:3px 8px;border-radius:12px;color:{};font-weight:600;font-size:12px;">{}</span>',
                color,
                obj.payment.get_status_display()
            )
        return "—"
    payment_status_display.short_description = "Payment"

    def get_fieldsets(self, request, obj=None):
        return [
            ("Booking Details", {"fields": ("user", "time_slot", "package", "status", "notes")}),
            ("Jumper Eligibility", {"fields": ("jumper_age", "jumper_weight_kg")}),
            ("System Metadata", {"fields": ("created_at",)}),
        ]

    def mark_confirmed(self, request, queryset):
        rows = queryset.update(status="confirmed")
        self.message_user(request, f"{rows} booking(s) marked as Confirmed.")
    mark_confirmed.short_description = "Mark selected bookings as Confirmed"

    def mark_completed(self, request, queryset):
        rows = queryset.update(status="completed")
        self.message_user(request, f"{rows} booking(s) marked as Completed.")
    mark_completed.short_description = "Mark selected bookings as Completed"

    def mark_cancelled(self, request, queryset):
        rows = queryset.update(status="cancelled")
        self.message_user(request, f"{rows} booking(s) marked as Cancelled.")
    mark_cancelled.short_description = "Mark selected bookings as Cancelled"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "formatted_amount", "method", "status", "paid_at")
    list_filter = ("status", "method")
    search_fields = ("booking__user__username", "booking__id")
    date_hierarchy = "paid_at"
    readonly_fields = ("paid_at",)
    actions = ["mark_paid", "mark_refunded"]

    def formatted_amount(self, obj):
        return f"₦{obj.amount:,.0f}"
    formatted_amount.short_description = "Amount"

    def mark_paid(self, request, queryset):
        from django.utils import timezone
        rows = queryset.update(status="paid", paid_at=timezone.now())
        self.message_user(request, f"{rows} payment(s) marked as Paid.")
    mark_paid.short_description = "Mark selected payments as Paid"

    def mark_refunded(self, request, queryset):
        rows = queryset.update(status="refunded")
        self.message_user(request, f"{rows} payment(s) marked as Refunded.")
    mark_refunded.short_description = "Mark selected payments as Refunded"


def custom_admin_index(request, extra_context=None):
    """Custom dashboard for /admin/ — replaces the default index page with real operations KPIs."""
    today = date.today()
    week_ahead = today + timedelta(days=7)
    last_30 = today - timedelta(days=30)

    kpis = {
        "today_count": Booking.objects.filter(time_slot__date=today).exclude(status="cancelled").count(),
        "week_count": Booking.objects.filter(time_slot__date__gte=today, time_slot__date__lte=week_ahead).exclude(status="cancelled").count(),
        "cancelled_today": Booking.objects.filter(time_slot__date=today, status="cancelled").count(),
        "revenue_30d": Payment.objects.filter(status="paid", paid_at__date__gte=last_30).aggregate(total=Sum("amount"))["total"] or 0,
    }

    recent_bookings = (
        Booking.objects
        .select_related("user", "time_slot__drop_zone", "package", "payment")
        .order_by("-created_at")[:8]
    )
    upcoming_slots = (
        TimeSlot.objects
        .filter(date__gte=today, date__lte=week_ahead)
        .select_related("drop_zone")
        .order_by("date", "start_time")[:8]
    )

    context = {
        **admin.site.each_context(request),
        "title": "Skyeman Operations Dashboard",
        "kpis": kpis,
        "recent_bookings": recent_bookings,
        "upcoming_slots": upcoming_slots,
        "today": today,
    }
    return render(request, "admin/skyeman_dashboard.html", context)


# Replace the default index view with the custom dashboard
admin.site.index = custom_admin_index
