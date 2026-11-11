from django.contrib import admin

from .models import BlockedDate, Booking, WeeklyAvailability


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["reference", "name", "mobile", "mode", "date", "start_time", "status"]
    list_filter = ["status", "mode", "date"]
    search_fields = ["reference", "name", "mobile"]


@admin.register(WeeklyAvailability)
class WeeklyAvailabilityAdmin(admin.ModelAdmin):
    list_display = ["weekday", "start_time", "end_time", "slot_minutes", "is_active"]


admin.site.register(BlockedDate)
