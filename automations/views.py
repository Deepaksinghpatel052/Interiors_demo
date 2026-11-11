from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core import locked
from core.models import StudioSettings
from core.permissions import owner_required, team_required

from . import engine
from .models import Automation, AutomationLog, MessageTemplate

SAMPLE = {
    "name": "Priya", "meeting": "studio consultation", "date": "Sat, 14-11-2026", "time": "11:00 AM",
    "reference": "BK7Q2M", "quote_number": "QT/2026-27/014", "amount": "₹4,85,600", "link": "/portal/",
    "invoice_number": "INV/2026-27/0009", "due_date": "18-11-2026", "mobile": "98XXXXXX10",
    "source": "Website", "details": "3 BHK flat, ₹8–15 lakh", "days": 4, "stage": "Contacted",
}

LOCKED_AUTOMATIONS = ["whatsapp_api", "lead_ads", "gcal_sync", "email_campaigns", "google_reviews"]
MAX_BODY = 1000


def _module_on():
    return StudioSettings.load().module_automation


@team_required
def automations(request):
    if not _module_on():
        return render(request, "automations/off.html", status=404)
    engine.ensure_templates()
    studio = StudioSettings.load()
    ctx = {**SAMPLE, "studio": studio.name}
    cards = []
    for t in MessageTemplate.objects.all():
        when, icon = engine.DESCRIPTIONS.get(t.key, ("", "lightning"))
        cards.append({"t": t, "when": when, "icon": icon, "preview": engine.render(t.body, ctx),
                      "placeholders": engine.PLACEHOLDERS.get(t.key, []),
                      "count": AutomationLog.objects.filter(automation=t.key).count(),
                      "owner_msg": t.key in (Automation.NEW_LEAD, Automation.LEAD_FOLLOWUP)})
    kind = request.GET.get("kind", "")
    logs = AutomationLog.objects.select_related("lead", "booking", "invoice", "quotation")
    if kind in Automation.values:
        logs = logs.filter(automation=kind)
    page = Paginator(logs, 15).get_page(request.GET.get("page"))
    for log in page:
        log.wa_url = engine.whatsapp_url(log)
    return render(request, "automations/index.html", {
        "cards": cards, "page": page, "kind": kind, "kinds": Automation.choices,
        "total": AutomationLog.objects.count(), "active_count": sum(1 for c in cards if c["t"].is_active),
        "locked_items": [locked.get(k) for k in LOCKED_AUTOMATIONS], "max_body": MAX_BODY,
    })


@owner_required
@require_POST
def template_save(request, key):
    t = get_object_or_404(MessageTemplate, key=key)
    if request.POST.get("action") == "reset":
        t.body = engine.DEFAULT_TEMPLATES[key]
        t.save(update_fields=["body", "updated_at"])
        messages.success(request, f"“{t.get_key_display()}” restored to the default message.")
        return redirect("automations:index")
    body = (request.POST.get("body") or "").strip().replace("\r\n", "\n")
    if not body:
        messages.error(request, "The message cannot be empty.")
    elif len(body) > MAX_BODY:
        messages.error(request, f"Please keep the message under {MAX_BODY} characters.")
    elif engine.check(body):
        messages.error(request, engine.check(body))
    else:
        t.body = body
        t.save(update_fields=["body", "updated_at"])
        messages.success(request, f"“{t.get_key_display()}” message saved.")
    return redirect("automations:index")


@owner_required
@require_POST
def template_toggle(request, key):
    t = get_object_or_404(MessageTemplate, key=key)
    t.is_active = not t.is_active
    t.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"“{t.get_key_display()}” switched {'on' if t.is_active else 'off'}.")
    return redirect("automations:index")


@team_required
@require_POST
def run_now(request):
    made = engine.run_scheduled()
    if made:
        messages.success(request, f"Daily checks done: {len(made)} message{'s' if len(made) != 1 else ''} prepared.")
    else:
        messages.info(request, "Daily checks done: nothing due right now (each reminder is prepared only once).")
    return redirect("automations:index")
