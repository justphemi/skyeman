"""Django admin customisations for the dropzones app."""
from django.contrib import admin
from .models import DropZone, JumpPackage, TimeSlot


class TimeSlotInline(admin.TabularInline):
    model = TimeSlot
    extra = 1
    fields = ("date", "start_time", "capacity", "status")
    show_change_link = True


@admin.register(DropZone)
class DropZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "address", "slots_count")
    list_filter = ("city",)
    search_fields = ("name", "city", "address", "description")
    inlines = [TimeSlotInline]

    def slots_count(self, obj):
        return obj.time_slots.count()
    slots_count.short_description = "Total Slots"


@admin.register(JumpPackage)
class JumpPackageAdmin(admin.ModelAdmin):
    list_display = ("name", "formatted_price", "min_age", "max_weight_kg", "duration_minutes")
    list_filter = ("name",)
    search_fields = ("name", "description")

    def formatted_price(self, obj):
        return f"₦{obj.price:,.0f}"
    formatted_price.short_description = "Price"


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "drop_zone", "date", "start_time", "capacity", "booked_display", "seats_left_display", "status")
    list_filter = ("status", "date", "drop_zone")
    search_fields = ("drop_zone__name",)
    date_hierarchy = "date"
    autocomplete_fields = ["drop_zone"]
    list_editable = ("status",)
    actions = ["mark_open", "mark_full", "mark_cancelled"]

    def booked_display(self, obj):
        return obj.booked_count
    booked_display.short_description = "Booked"

    def seats_left_display(self, obj):
        return obj.seats_left
    seats_left_display.short_description = "Remaining"

    def mark_open(self, request, queryset):
        rows = queryset.update(status="open")
        self.message_user(request, f"{rows} time slot(s) set to Open.")
    mark_open.short_description = "Mark selected slots as Open"

    def mark_full(self, request, queryset):
        rows = queryset.update(status="full")
        self.message_user(request, f"{rows} time slot(s) set to Full.")
    mark_full.short_description = "Mark selected slots as Full"

    def mark_cancelled(self, request, queryset):
        rows = queryset.update(status="cancelled")
        self.message_user(request, f"{rows} time slot(s) marked as Cancelled.")
    mark_cancelled.short_description = "Mark selected slots as Cancelled (Weather)"
