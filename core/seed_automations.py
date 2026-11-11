"""Automation templates + a realistic log spread over the last few days (all simulated, never sent)."""
from datetime import timedelta

from django.utils import timezone

from automations import engine
from automations.models import AutomationLog


def seed_automations(out):
    from bookings.models import Booking
    from crm.models import Lead
    from finance.models import Quotation

    engine.ensure_templates()
    AutomationLog.objects.all().delete()        # drop the burst created by signals while seeding
    now = timezone.now()
    plan = []
    for i, lead in enumerate(Lead.objects.order_by("-created_at")[:6]):
        plan.append((engine.lead_created, lead, timedelta(days=i, hours=2 + i)))
    for i, b in enumerate(Booking.objects.filter(status=Booking.Status.CONFIRMED).order_by("-created_at")[:5]):
        plan.append((engine.booking_created, b, timedelta(days=i, hours=1, minutes=10 * i)))
    for i, q in enumerate(Quotation.objects.filter(sent_at__isnull=False).order_by("-sent_at")[:3]):
        plan.append((engine.quotation_sent, q, timedelta(days=1 + 2 * i, hours=5)))
    for fn, obj, ago in plan:
        log = fn(obj)
        if log:
            AutomationLog.objects.filter(pk=log.pk).update(created_at=now - ago)
    made = engine.run_scheduled()             # reminders / payment due / follow-ups based on today's data
    for i, log in enumerate(made):
        AutomationLog.objects.filter(pk=log.pk).update(created_at=now - timedelta(minutes=30 + 7 * i))
    out.write(f"  automations: {AutomationLog.objects.count()} log entries")
