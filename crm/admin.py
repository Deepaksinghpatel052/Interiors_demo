from django.contrib import admin

from .models import Lead, LeadActivity


class ActivityInline(admin.TabularInline):
    model = LeadActivity
    extra = 0


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["name", "mobile", "source", "stage", "property_type", "created_at"]
    list_filter = ["stage", "source"]
    search_fields = ["name", "mobile", "email"]
    inlines = [ActivityInline]
