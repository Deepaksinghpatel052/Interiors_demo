from django.contrib import admin

from .models import FeatureInterest, ModuleRequest, StudioSettings


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
        ("Extra features (switch on when the studio requests them)", {"fields": ["module_tour360"]}),
    ]

    def has_add_permission(self, request):
        return not StudioSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FeatureInterest)
class FeatureInterestAdmin(admin.ModelAdmin):
    list_display = ["feature", "created_at"]
    list_filter = ["feature"]


@admin.register(ModuleRequest)
class ModuleRequestAdmin(admin.ModelAdmin):
    """Studios asking for an extra feature. “Approve & switch on” turns the feature on for the studio."""
    list_display = ["created_at", "feature_label", "requested_by", "short_note", "status", "decided_at"]
    list_filter = ["status", "feature"]
    readonly_fields = ["feature", "requested_by", "note", "created_at", "decided_at"]
    fields = ["feature", "requested_by", "note", "status", "created_at", "decided_at"]
    actions = ["approve", "decline"]

    @admin.display(description="Feature")
    def feature_label(self, obj):
        return obj.feature_label

    @admin.display(description="Message")
    def short_note(self, obj):
        return (obj.note[:80] + "…") if len(obj.note) > 80 else obj.note

    def has_add_permission(self, request):
        return False

    def _switch(self, keys, on):
        s = StudioSettings.load()
        for k in keys:
            if hasattr(s, "module_" + k):
                setattr(s, "module_" + k, on)
        s.save()

    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        if "status" in form.changed_data:
            obj.decided_at = timezone.now() if obj.status != ModuleRequest.Status.PENDING else None
            if obj.status == ModuleRequest.Status.APPROVED:
                self._switch([obj.feature], True)
        super().save_model(request, obj, form, change)

    @admin.action(description="Approve & switch the feature on")
    def approve(self, request, queryset):
        from django.utils import timezone
        keys = set(queryset.values_list("feature", flat=True))
        self._switch(keys, True)
        queryset.update(status=ModuleRequest.Status.APPROVED, decided_at=timezone.now())
        self.message_user(request, "Switched on: " + ", ".join(sorted(
            ModuleRequest(feature=k).feature_label for k in keys)) + ". The studio can use it right away.")

    @admin.action(description="Decline")
    def decline(self, request, queryset):
        from django.utils import timezone
        n = queryset.update(status=ModuleRequest.Status.DECLINED, decided_at=timezone.now())
        self.message_user(request, f"{n} request(s) declined.")


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
