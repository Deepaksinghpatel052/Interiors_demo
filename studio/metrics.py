"""Numbers for the owner dashboard and reports. Later phases add money KPIs here."""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from bookings.models import Booking
from crm.models import Lead

from .models import ClientProject, Milestone, Task

FUNNEL = [
    ("All leads", None),
    ("Contacted+", ["contacted", "consultation", "site_visit", "proposal", "won"]),
    ("Consultation+", ["consultation", "site_visit", "proposal", "won"]),
    ("Site visit+", ["site_visit", "proposal", "won"]),
    ("Proposal+", ["proposal", "won"]),
    ("Won", ["won"]),
]


def week_start(today=None):
    today = today or timezone.localdate()
    return today - timedelta(days=today.weekday())


def kpis():
    today = timezone.localdate()
    monday = week_start(today)
    leads = Lead.objects.all()
    decided = leads.filter(stage__in=["won", "lost"]).count()
    won = leads.filter(stage="won").count()
    return {
        "new_leads_week": leads.filter(created_at__date__gte=monday).count(),
        "consultations": Booking.objects.filter(date__gte=today).exclude(status="cancelled").count(),
        "active_projects": ClientProject.objects.exclude(stage=ClientProject.Stage.COMPLETED).count(),
        "conversion": round(100 * won / decided) if decided else 0,
        "open_tasks": Task.objects.exclude(status=Task.Status.DONE).count(),
        **money_kpis(today),
    }


def money_kpis(today=None):
    from django.db.models import Sum

    from finance.models import Invoice, Payment, Quotation
    today = today or timezone.localdate()
    month_start = today.replace(day=1)
    sent = Quotation.objects.filter(sent_at__date__gte=today - timedelta(days=30))
    open_invoices = Invoice.objects.filter(status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL]).prefetch_related("payments")
    return {
        "quotes_sent": sent.count(),
        "quotes_sent_value": sent.aggregate(t=Sum("grand_total"))["t"] or 0,
        "pending_payments": sum((i.balance for i in open_invoices), 0),
        "overdue_invoices": sum(1 for i in open_invoices if i.is_overdue),
        "revenue_month": Payment.objects.filter(date__gte=month_start).aggregate(t=Sum("amount"))["t"] or 0,
    }


def revenue_by_month(months=6, today=None):
    """[(label, amount)] of payments received per month, oldest first."""
    from django.db.models import Sum

    from finance.models import Payment
    today = today or timezone.localdate()
    out = []
    y, m = today.year, today.month
    for _ in range(months):
        start = today.replace(year=y, month=m, day=1)
        end = start.replace(year=y + (m == 12), month=1 if m == 12 else m + 1)
        total = Payment.objects.filter(date__gte=start, date__lt=end).aggregate(t=Sum("amount"))["t"] or 0
        out.append((start.strftime("%b %y"), float(total)))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return list(reversed(out))


def leads_by_source():
    rows = dict(Lead.objects.values_list("source").annotate(n=Count("id")).values_list("source", "n"))
    return [(label, rows.get(value, 0)) for value, label in Lead.Source.choices]


def funnel():
    out = []
    for label, stages in FUNNEL:
        qs = Lead.objects.all() if stages is None else Lead.objects.filter(stage__in=stages)
        out.append((label, qs.count()))
    return out


def projects_by_stage():
    rows = dict(ClientProject.objects.values_list("stage").annotate(n=Count("id")).values_list("stage", "n"))
    return [(label, rows.get(value, 0)) for value, label in ClientProject.Stage.choices]


def today_schedule(user=None):
    today = timezone.localdate()
    bookings = Booking.objects.filter(date=today).exclude(status="cancelled").select_related("lead")
    tasks = Task.objects.filter(due_date=today).exclude(status=Task.Status.DONE).select_related("project", "assigned_to")
    return {"bookings": bookings, "tasks": tasks}


def overdue():
    today = timezone.localdate()
    return {k: list(v) for k, v in {
        "tasks": Task.objects.filter(due_date__lt=today).exclude(status=Task.Status.DONE)
                     .select_related("project", "assigned_to")[:8],
        "milestones": Milestone.objects.filter(due_date__lt=today).exclude(status=Milestone.Status.DONE)
                          .exclude(project__stage=ClientProject.Stage.COMPLETED).select_related("project")[:8],
        "followups": Lead.objects.filter(follow_up_date__lt=today)
                         .exclude(stage__in=["won", "lost"])[:8],
        "untouched": Lead.objects.filter(stage="new", updated_at__lt=timezone.now() - timedelta(days=3))[:8],
    }.items()}


def upcoming_bookings(days=7):
    today = timezone.localdate()
    return (Booking.objects.filter(date__gte=today, date__lte=today + timedelta(days=days))
            .exclude(status="cancelled").select_related("lead"))


def recent_activity(limit=8):
    from crm.models import LeadActivity
    return LeadActivity.objects.select_related("lead", "user")[:limit]
