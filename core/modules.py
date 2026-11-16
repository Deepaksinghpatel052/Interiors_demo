"""Module feature flags: one codebase sold as small or complete packages.

`module_for(match)` maps a resolved URL to the StudioSettings flag that must be on for it to work.
The middleware returns a clean "not part of your package" page (404) for switched-off modules,
and templates hide their menu items (or show a locked teaser when `show_locked_teasers` is on).
"""
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .models import StudioSettings

MODULES = [  # flag, label, icon, what it adds
    ("website", "Website", "globe2", "Public website: portfolio, services, style quiz, estimator and online booking."),
    ("cms", "Website CMS", "pencil-square", "Edit projects, photos, services, testimonials, FAQs and homepage text yourself."),
    ("erp", "Studio ERP", "kanban", "Leads, bookings, projects, quotations, invoices, vendors and reports."),
    ("portal", "Client portal", "person-heart", "Clients approve designs, see progress and download documents online."),
    ("automation", "Automation", "lightning-charge", "Ready-to-send WhatsApp confirmations, reminders and follow-ups."),
    ("ai", "AI assistant", "stars", "Website and studio assistants that answer from your own knowledge base."),
]

# Extra features: not part of any package. Off until the studio requests them (button in the studio) and
# DEVNIXPLUS switches them on in the Django admin (Studio settings → Extra features, or approve the request).
EXTRA_FEATURES = {
    "tour360": {
        "label": "360° house tour", "icon": "arrow-repeat",
        "what": "Visitors walk through a finished home in 360° on the portfolio page — room by room, with "
                "clickable dots that explain the furniture, lighting and materials.",
        "benefit": "Prospects feel the quality of your work before they ever meet you, and enquire with more confidence.",
        "manage_url": "cms:tours",
    },
}


def extra_on(key, studio=None):
    studio = studio or StudioSettings.load()
    return bool(getattr(studio, "module_" + key, False))


def extra_status(key, studio=None):
    """'on', 'requested' (waiting for DEVNIXPLUS) or 'off'."""
    from .models import ModuleRequest
    if extra_on(key, studio):
        return "on"
    if ModuleRequest.objects.filter(feature=key, status=ModuleRequest.Status.PENDING).exists():
        return "requested"
    return "off"


# studio pages that belong to the ERP; the rest of /studio/ (settings, team, availability) is always available
ERP_STUDIO_URLS = {
    "dashboard", "leads", "lead_create", "lead_move", "lead_detail", "lead_note", "lead_convert",
    "bookings", "booking_events", "booking_move", "booking_status",
    "projects", "project_create", "project_move", "project_detail", "project_edit", "task_add", "milestone_add",
    "space_add", "proposal_add", "update_add", "document_add", "tasks", "task_status", "task_delete",
    "milestone_status", "space_delete", "proposal_share", "document_delete", "client_activity",
    "reports", "report_csv",
}
NAMESPACE_MODULE = {"website": "website", "bookings": "website", "portal": "portal", "finance": "erp",
                    "automations": "automation", "assistant": "ai", "cms": "cms"}
ALWAYS_ON = {("", "landing"), ("website", "why"), ("website", "privacy"), ("website", "credits")}


def module_for(match):
    if match is None:
        return None
    ns, name = match.namespace, match.url_name
    if (ns, name) in ALWAYS_ON:
        return None
    if ns == "studio":
        return "erp" if name in ERP_STUDIO_URLS else None
    return NAMESPACE_MODULE.get(ns)


def is_on(module, studio=None):
    studio = studio or StudioSettings.load()
    return bool(getattr(studio, "module_" + module, True))


def studio_home_url(studio=None):
    """Where the studio lands when the ERP dashboard is not part of the package."""
    studio = studio or StudioSettings.load()
    if studio.module_erp:
        return "studio:dashboard"
    if studio.module_cms:
        return "cms:index"
    return "studio:settings"


class ModuleGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        module = module_for(request.resolver_match)
        if module is None:
            return None
        studio = StudioSettings.load()
        if is_on(module, studio):
            return None
        match = request.resolver_match
        if match.namespace == "studio" and match.url_name == "dashboard":
            return redirect(studio_home_url(studio))
        if match.namespace == "website" and match.url_name == "home":
            return redirect("core:login")
        if request.path.startswith(("/api/", "/studio/api/")) or request.headers.get("Accept", "").startswith("application/json"):
            return JsonResponse({"error": "This module is not part of this package."}, status=404)
        label = dict((m[0], m[1]) for m in MODULES)[module]
        template = "core/module_off_studio.html" if request.path.startswith("/studio/") else "core/module_off.html"
        return render(request, template, {"module_label": label, "module_key": module}, status=404)
