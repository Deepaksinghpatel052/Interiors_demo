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
    actions = ["export_csv", "mark_contacted", "make_demo_links"]

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

    @admin.action(description="Create a personal demo link for each selected enquiry")
    def make_demo_links(self, request, queryset):
        made = 0
        for e in queryset:
            if not e.demo_links.exists():
                DemoLink.objects.create(business_name=e.studio_name or e.name, contact_name=e.name,
                                        mobile=e.mobile, city=e.city, enquiry=e)
                made += 1
        self.message_user(request, f"{made} demo link(s) created. Open “Client demo links” to copy or send them.")
        return redirect("admin:core_demolink_changelist")

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


# ---------------------------------------------------------------- DEVNIXPLUS: personal demo links for prospects
import contextvars  # noqa: E402
from datetime import timedelta  # noqa: E402

from django.conf import settings  # noqa: E402
from django.shortcuts import redirect  # noqa: E402
from django.utils.html import format_html_join  # noqa: E402
from django.utils.timesince import timesince  # noqa: E402

from .models import DemoLink, DemoVisit  # noqa: E402

_origin = contextvars.ContextVar("admin_origin", default="")

COPY_JS = ("var u=this.dataset.url;navigator.clipboard.writeText(u).then(()=>{this.textContent='Copied ✓';"
           "setTimeout(()=>this.textContent='Copy link',1500)},()=>prompt('Copy this link:',u));return false;")


def _ago(dt):
    if not dt:
        return ""
    return timesince(dt).split(",")[0] + " ago"


class DemoVisitInline(admin.TabularInline):
    model = DemoVisit
    extra = 0
    max_num = 0
    can_delete = False
    fields = ["when", "kind", "title", "path", "device"]
    readonly_fields = fields
    verbose_name_plural = "What they did (newest first)"

    @admin.display(description="When")
    def when(self, obj):
        return timezone.localtime(obj.created_at).strftime("%d-%m-%Y %I:%M %p")


@admin.register(DemoLink)
class DemoLinkAdmin(admin.ModelAdmin):
    """One personal demo link per prospect: the demo shows their business name, and opens/pages/clicks are recorded."""
    list_display = ["business_name", "contact_name", "status", "visits", "page_views", "last_seen", "link_buttons"]
    list_filter = ["is_active", ("first_opened_at", admin.EmptyFieldListFilter), "created_at"]
    search_fields = ["business_name", "contact_name", "mobile", "city", "slug"]
    autocomplete_fields = ["enquiry"]
    readonly_fields = ["link_box", "first_opened_at", "last_seen_at", "visits", "page_views", "interest", "created_at"]
    inlines = [DemoVisitInline]

    def get_fieldsets(self, request, obj=None):
        sets = [
            ("Client", {"fields": ["business_name", "contact_name", "mobile", "city", "enquiry"]}),
            ("Branding (optional)", {"fields": ["logo", "accent_color"]}),
            ("Link", {"fields": (["link_box"] if obj else []) + ["slug", "is_active"]}),
        ]
        if obj:
            sets.append(("Activity", {"fields": ["first_opened_at", "last_seen_at", "visits", "page_views", "interest"]}))
        sets.append(("Notes", {"fields": ["notes", "created_at"] if obj else ["notes"]}))
        return sets

    def changelist_view(self, request, extra_context=None):
        _origin.set(request.build_absolute_uri("/").rstrip("/"))
        return super().changelist_view(request, extra_context)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        _origin.set(request.build_absolute_uri("/").rstrip("/"))
        return super().changeform_view(request, object_id, form_url, extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            self.message_user(request, f"Link ready for {obj.business_name}: copy it or send it on WhatsApp below.")
            return redirect("admin:core_demolink_change", obj.pk)
        return super().response_add(request, obj, post_url_continue)

    def _url(self, obj):
        return _origin.get() + obj.get_absolute_url()

    def _wa(self, obj):
        first = obj.contact_name.split()[0] if obj.contact_name else ""
        number = "".join(c for c in obj.mobile if c.isdigit())
        if len(number) == 10:
            number = "91" + number
        text = (f"Hi {first}, " if first else "Hi, ") + (
            f"this is {settings.DEVNIX_NAME}. We have set up a demo of the studio software for {obj.business_name} "
            f"— your website, client portal and studio ERP in one place. Open it here: {self._url(obj)}")
        return wa_link(number, text) if number else wa_link("", text)

    @admin.display(description="Status", ordering="last_seen_at")
    def status(self, obj):
        if not obj.is_active:
            return format_html('<span style="color:#888">Switched off</span>')
        if not obj.first_opened_at:
            return format_html('<span style="color:#b26a00;font-weight:600">● Not opened yet</span>')
        recent = obj.last_seen_at and timezone.now() - obj.last_seen_at < timedelta(days=1)
        return format_html('<span style="color:{};font-weight:600">● Opened{}</span>',
                           "#1a7f37" if recent else "#0969da", " — active today" if recent else "")

    @admin.display(description="Last seen", ordering="last_seen_at")
    def last_seen(self, obj):
        return _ago(obj.last_seen_at) or "—"

    def _buttons(self, obj):
        return format_html(
            '<a class="button" href="#" data-url="{}" onclick="{}">Copy link</a> '
            '<a class="button" href="{}" target="_blank" rel="noopener">Send on WhatsApp</a> '
            '<a class="button" href="{}?preview=1" target="_blank" rel="noopener" title="Opens the demo as they see it, '
            'without counting as their visit">Preview</a>',
            self._url(obj), COPY_JS, self._wa(obj), obj.get_absolute_url())

    @admin.display(description="Link")
    def link_buttons(self, obj):
        return self._buttons(obj)

    @admin.display(description="Their link")
    def link_box(self, obj):
        return format_html('<code style="font-size:14px">{}</code><div style="margin-top:8px">{}</div>',
                           self._url(obj), self._buttons(obj))

    @admin.display(description="What they looked at most")
    def interest(self, obj):
        from django.db.models import Count
        rows = (obj.events.exclude(kind="open").values("title").annotate(n=Count("id")).order_by("-n")[:8])
        if not rows:
            return "Nothing yet."
        return format_html_join("", "<div>{} <span style='color:#888'>× {}</span></div>",
                                ((r["title"] or "—", r["n"]) for r in rows))


if not settings.DEMO_MODE:   # a client's own server never shows the seller's sales tools
    admin.site.unregister(DemoLink)
