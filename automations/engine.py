"""Simulated automations: messages are generated from editable templates and logged (never sent).
Each log entry carries a wa.me link so the studio can send it from its own WhatsApp in one tap."""
import string
from datetime import timedelta

from django.utils import timezone

from core.models import StudioSettings
from core.templatetags.studio import format_inr, wa_link

from .models import Automation, AutomationLog, MessageTemplate

DEFAULT_TEMPLATES = {
    Automation.BOOKING_CONFIRMATION:
        "Namaste {name} 🙏\nYour {meeting} with {studio} is confirmed for {date} at {time}.\n"
        "Booking reference: {reference}\nTo reschedule, just reply to this message. See you soon!",
    Automation.CONSULTATION_REMINDER:
        "Hi {name}, a gentle reminder: your {meeting} with {studio} is tomorrow, {date} at {time}.\n"
        "Please keep your floor plan or a few photos of the space handy. Reply YES to confirm.",
    Automation.QUOTATION_SENT:
        "Hi {name}, your quotation {quote_number} from {studio} is ready — total {amount} incl. GST.\n"
        "You can view and download it in your client portal: {link}\nHappy to walk you through it on a call.",
    Automation.PAYMENT_DUE:
        "Hi {name}, a friendly reminder from {studio}: invoice {invoice_number} for {amount} is due on {due_date}.\n"
        "You can pay by UPI or bank transfer. Please share the reference once paid. Thank you!",
    Automation.NEW_LEAD:
        "🔔 New lead: {name} ({mobile}) via {source}.\n{details}\nOpen the lead: {link}",
    Automation.LEAD_FOLLOWUP:
        "⏰ Follow up today: {name} ({mobile}) has had no update for {days} days. Stage: {stage}.\nOpen the lead: {link}",
}

PLACEHOLDERS = {
    Automation.BOOKING_CONFIRMATION: ["name", "studio", "meeting", "date", "time", "reference"],
    Automation.CONSULTATION_REMINDER: ["name", "studio", "meeting", "date", "time", "reference"],
    Automation.QUOTATION_SENT: ["name", "studio", "quote_number", "amount", "link"],
    Automation.PAYMENT_DUE: ["name", "studio", "invoice_number", "amount", "due_date"],
    Automation.NEW_LEAD: ["name", "mobile", "source", "details", "link", "studio"],
    Automation.LEAD_FOLLOWUP: ["name", "mobile", "days", "stage", "link", "studio"],
}

DESCRIPTIONS = {
    Automation.BOOKING_CONFIRMATION: ("Instantly, when a visitor books online", "calendar2-check"),
    Automation.CONSULTATION_REMINDER: ("Daily check · consultations tomorrow", "alarm"),
    Automation.QUOTATION_SENT: ("When a quotation is sent to the client", "receipt"),
    Automation.PAYMENT_DUE: ("Daily check · invoices due in 2 days or overdue", "wallet2"),
    Automation.NEW_LEAD: ("Instantly, to the owner, for every new lead", "person-plus"),
    Automation.LEAD_FOLLOWUP: ("Daily check · leads untouched for 3 days", "telephone-outbound"),
}


def ensure_templates():
    for key, body in DEFAULT_TEMPLATES.items():
        MessageTemplate.objects.get_or_create(key=key, defaults={"body": body})


def render(body, context):
    """Fill only known {placeholders}; anything else (or attribute/index access) is left untouched.
    A malformed template (e.g. a stray brace) is returned as written instead of raising."""
    out = []
    try:
        parsed = list(string.Formatter().parse(body or ""))
    except ValueError:
        return body or ""
    for literal, field, spec, conv in parsed:
        out.append(literal)
        if field is None:
            continue
        if field.isidentifier() and field in context:
            out.append(str(context[field]))
        else:
            out.append("{" + field + (("!" + conv) if conv else "") + ((":" + spec) if spec else "") + "}")
    return "".join(out)


def check(body):
    """Return an error message for a template the owner is about to save, or None."""
    try:
        fields = [f for _, f, _, _ in string.Formatter().parse(body) if f is not None]
    except ValueError:
        return "Curly braces must come in pairs, like {name}."
    bad = [f for f in fields if not f.isidentifier()]
    return f"“{{{bad[0]}}}” is not a valid placeholder." if bad else None


def _template(key):
    ensure_templates()
    t = MessageTemplate.objects.get(key=key)
    return t if t.is_active else None


def fire(key, *, name, phone="", to_owner=False, context=None, **links):
    """Generate + log one message. Returns the log entry, or None when the automation is switched off."""
    s = StudioSettings.load()
    if not s.module_automation:
        return None
    t = _template(key)
    if t is None:
        return None
    ctx = {"studio": s.name, "name": name, **(context or {})}
    return AutomationLog.objects.create(automation=key, recipient_name=name[:100], recipient_phone=(phone or "")[:15],
                                        to_owner=to_owner, message=render(t.body, ctx), **links)


def whatsapp_url(log):
    number = StudioSettings.load().whatsapp if log.to_owner else log.recipient_phone
    digits = "".join(c for c in number if c.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return wa_link(digits, log.message)


# ------------------------------------------------------------------------------ event triggers
def booking_created(booking):
    return fire(Automation.BOOKING_CONFIRMATION, name=booking.name, phone=booking.mobile, booking=booking,
                lead=booking.lead, context={"meeting": booking.get_mode_display().lower().replace("at our studio", "studio consultation")
                                            .replace("online video call", "online consultation"),
                                            "date": booking.date.strftime("%a, %d-%m-%Y"),
                                            "time": booking.start_time.strftime("%I:%M %p").lstrip("0"),
                                            "reference": booking.reference})


def lead_created(lead):
    s = StudioSettings.load()
    details = ", ".join(x for x in [lead.get_property_type_display() if lead.property_type else "",
                                    lead.get_budget_band_display() if lead.budget_band else "",
                                    (lead.message or "")[:80]] if x) or "No details yet"
    return fire(Automation.NEW_LEAD, name=lead.name, phone=s.whatsapp, to_owner=True, lead=lead,
                context={"mobile": lead.mobile, "source": lead.get_source_display(), "details": details,
                         "link": f"/studio/leads/{lead.pk}/"})


def quotation_sent(q):
    return fire(Automation.QUOTATION_SENT, name=q.client_name, phone=q.client_mobile, quotation=q, lead=q.lead,
                project=q.project, context={"quote_number": q.display_number, "amount": format_inr(q.grand_total),
                                            "link": "/portal/documents/"})


# ------------------------------------------------------------------------------ scheduled checks
def run_scheduled(now=None):
    """Daily checks (cron in production; a 'Run now' button in the demo). Each item is messaged at most once per window."""
    from bookings.models import Booking
    from crm.models import Lead
    from finance.models import Invoice

    now = now or timezone.now()
    today = timezone.localdate(now)
    made = []

    tomorrow = today + timedelta(days=1)
    for b in Booking.objects.filter(date=tomorrow, status=Booking.Status.CONFIRMED):
        if not AutomationLog.objects.filter(automation=Automation.CONSULTATION_REMINDER, booking=b).exists():
            log = fire(Automation.CONSULTATION_REMINDER, name=b.name, phone=b.mobile, booking=b, lead=b.lead,
                       context={"meeting": "consultation" if b.kind == "consultation" else "site visit",
                                "date": b.date.strftime("%a, %d-%m-%Y"),
                                "time": b.start_time.strftime("%I:%M %p").lstrip("0"), "reference": b.reference})
            made.append(log)

    recent = now - timedelta(days=3)
    for inv in Invoice.objects.filter(status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL],
                                      due_date__lte=today + timedelta(days=2)).select_related("project"):
        if inv.balance <= 0 or AutomationLog.objects.filter(automation=Automation.PAYMENT_DUE, invoice=inv,
                                                            created_at__gte=recent).exists():
            continue
        made.append(fire(Automation.PAYMENT_DUE, name=inv.client_name, phone=inv.project.client_mobile,
                         invoice=inv, project=inv.project,
                         context={"invoice_number": inv.number, "amount": format_inr(inv.balance),
                                  "due_date": inv.due_date.strftime("%d-%m-%Y")}))

    s = StudioSettings.load()
    stale = now - timedelta(days=3)
    for lead in Lead.objects.filter(stage__in=[Lead.Stage.NEW, Lead.Stage.CONTACTED], updated_at__lt=stale):
        if AutomationLog.objects.filter(automation=Automation.LEAD_FOLLOWUP, lead=lead, created_at__gte=recent).exists():
            continue
        made.append(fire(Automation.LEAD_FOLLOWUP, name=lead.name, phone=s.whatsapp, to_owner=True, lead=lead,
                         context={"mobile": lead.mobile, "days": (now - lead.updated_at).days,
                                  "stage": lead.get_stage_display(), "link": f"/studio/leads/{lead.pk}/"}))
    return [m for m in made if m]
