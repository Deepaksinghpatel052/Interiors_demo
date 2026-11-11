from django.contrib import admin

from .models import FeatureInterest, StudioSettings


@admin.register(StudioSettings)
class StudioSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Brand", {"fields": ["name", "tagline", "logo", "accent_color", "secondary_color", "dark_color"]}),
        ("Contact", {"fields": ["city", "address", "phone", "whatsapp", "email", "map_embed_query",
                                "instagram", "working_hours", "founded_year"]}),
        ("Website copy", {"fields": ["hero_title", "hero_subtitle", "about_text"]}),
        ("Tax & commercial", {"fields": ["legal_name", "gstin", "state_name", "default_gst_percent",
                                         "payment_schedule", "quotation_terms", "bank_details"]}),
        ("Cost estimator rates (₹ / sq ft)", {"fields": ["rate_essential", "rate_premium", "rate_luxury"]}),
        ("Sales", {"fields": ["easy_payment_text"]}),
        ("Modules", {"fields": ["module_website", "module_cms", "module_portal", "module_erp",
                                "module_automation", "module_ai", "show_locked_teasers"]}),
    ]

    def has_add_permission(self, request):
        return not StudioSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FeatureInterest)
class FeatureInterestAdmin(admin.ModelAdmin):
    list_display = ["feature", "created_at"]
    list_filter = ["feature"]


# ---------------------------------------------------------------- DEVNIXPLUS product enquiries (landing page)
import csv  # noqa: E402

from django.http import HttpResponse  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.utils.html import format_html  # noqa: E402

from .models import ProductEnquiry  # noqa: E402
from .templatetags.studio import wa_link  # noqa: E402


@admin.register(ProductEnquiry)
class ProductEnquiryAdmin(admin.ModelAdmin):
    list_display = ["created_at", "name", "studio_name", "city", "mobile_link", "interested", "team_size", "status"]
    list_display_links = ["created_at", "name"]
    list_editable = ["status"]
    list_filter = ["status", "team_size", "contact_pref", "created_at"]
    search_fields = ["name", "studio_name", "mobile", "email", "city", "message"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at", "updated_at", "ip", "source", "whatsapp_button", "modules_display"]
    fieldsets = [
        ("Who", {"fields": ["name", "studio_name", "city", "team_size"]}),
        ("Contact", {"fields": ["mobile", "whatsapp_button", "email", "contact_pref"]}),
        ("Enquiry", {"fields": ["modules_display", "message"]}),
        ("Follow-up", {"fields": ["status", "notes"]}),
        ("System", {"classes": ["collapse"], "fields": ["source", "ip", "created_at", "updated_at"]}),
    ]
    actions = ["export_csv", "mark_contacted"]

    def _wa(self, obj):
        first = obj.name.split()[0] if obj.name else ""
        return wa_link("91" + obj.mobile, f"Hi {first}, this is DEVNIXPLUS — thanks for your enquiry about the studio system.")

    @admin.display(description="Mobile", ordering="mobile")
    def mobile_link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', self._wa(obj), obj.mobile)

    @admin.display(description="Interested in")
    def interested(self, obj):
        return obj.modules_display

    @admin.display(description="WhatsApp")
    def whatsapp_button(self, obj):
        if not obj.pk:
            return "—"
        return format_html('<a class="button" href="{}" target="_blank" rel="noopener">Open WhatsApp chat</a>', self._wa(obj))

    @admin.action(description="Mark selected as contacted")
    def mark_contacted(self, request, queryset):
        n = queryset.filter(status=ProductEnquiry.Status.NEW).update(status=ProductEnquiry.Status.CONTACTED)
        self.message_user(request, f"{n} enquiries marked as contacted.")

    @admin.action(description="Export selected to CSV (Excel)")
    def export_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="product-enquiries-{timezone.localdate():%Y%m%d}.csv"'
        resp.write("\ufeff")
        w = csv.writer(resp)
        w.writerow(["Date", "Name", "Studio", "City", "Mobile", "Email", "Team size", "Interested in",
                    "Preferred contact", "Message", "Status", "Notes"])

        def safe(v):
            s = "" if v is None else str(v)
            return "'" + s if s[:1] in ("=", "+", "-", "@") else s
        for e in queryset:
            w.writerow([safe(v) for v in [timezone.localtime(e.created_at).strftime("%d-%m-%Y %H:%M"), e.name, e.studio_name,
                                          e.city, e.mobile, e.email, e.get_team_size_display(), e.modules_display,
                                          e.get_contact_pref_display(), e.message, e.get_status_display(), e.notes]])
        return resp
