"""Basic reports: leads by source, conversion, revenue by month, outstanding payments (+ CSV)."""
import csv
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone

from crm.models import Lead

PERIODS = [("3", "Last 3 months"), ("6", "Last 6 months"), ("12", "Last 12 months")]


def period_start(months, today=None):
    today = today or timezone.localdate()
    y, m = today.year, today.month - (months - 1)
    while m <= 0:
        y, m = y - 1, m + 12
    return today.replace(year=y, month=m, day=1)


def source_rows(start):
    qs = (Lead.objects.filter(created_at__date__gte=start).values("source")
          .annotate(n=Count("id"), won=Count("id", filter=Q(stage=Lead.Stage.WON)),
                    lost=Count("id", filter=Q(stage=Lead.Stage.LOST))))
    by = {r["source"]: r for r in qs}
    rows = []
    for value, label in Lead.Source.choices:
        r = by.get(value, {"n": 0, "won": 0, "lost": 0})
        rows.append({"source": label, "leads": r["n"], "won": r["won"], "lost": r["lost"],
                     "conversion": round(100 * r["won"] / r["n"], 1) if r["n"] else 0})
    return rows


def summary(start):
    rows = source_rows(start)
    leads = sum(r["leads"] for r in rows)
    won = sum(r["won"] for r in rows)
    lost = sum(r["lost"] for r in rows)
    return {"leads": leads, "won": won, "lost": lost, "open": leads - won - lost,
            "conversion": round(100 * won / leads, 1) if leads else 0,
            "decided_conversion": round(100 * won / (won + lost), 1) if won + lost else 0}


def outstanding(today=None):
    from finance.models import Invoice
    today = today or timezone.localdate()
    out = []
    for inv in (Invoice.objects.filter(status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL])
                .select_related("project").prefetch_related("payments").order_by("due_date", "date")):
        bal = inv.balance
        if bal <= 0:
            continue
        days = (today - inv.due_date).days if inv.due_date and inv.due_date < today else 0
        out.append({"invoice": inv, "balance": bal, "days_overdue": days,
                    "bucket": "Not yet due" if not days else "1–30 days" if days <= 30 else "31–60 days" if days <= 60 else "60+ days"})
    return out


def ageing(rows):
    buckets = {k: Decimal(0) for k in ["Not yet due", "1–30 days", "31–60 days", "60+ days"]}
    for r in rows:
        buckets[r["bucket"]] += r["balance"]
    return list(buckets.items())


def payments(start):
    from finance.models import Payment
    return Payment.objects.filter(date__gte=start).select_related("invoice", "invoice__project").order_by("-date", "-id")


# ------------------------------------------------------------------ CSV
def _csv(filename, header, rows):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.write("\ufeff")                       # Excel opens UTF-8 (₹, names) correctly with a BOM
    w = csv.writer(resp)
    w.writerow(header)
    for r in rows:
        w.writerow([_safe(c) for c in r])
    return resp


def _safe(value):
    """Neutralise spreadsheet formula injection in user-entered text."""
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def csv_export(kind, months):
    from .metrics import revenue_by_month
    start = period_start(months)
    stamp = timezone.localdate().strftime("%Y%m%d")
    if kind == "leads":
        rows = (Lead.objects.filter(created_at__date__gte=start).select_related("assigned_to").order_by("-created_at"))
        return _csv(f"leads-{stamp}.csv", ["Date", "Name", "Mobile", "City", "Source", "Stage", "Property", "Budget", "Assigned to"],
                    [(timezone.localtime(l.created_at).strftime("%d-%m-%Y"), l.name, l.mobile, l.city, l.get_source_display(),
                      l.get_stage_display(), l.get_property_type_display() if l.property_type else "",
                      l.get_budget_band_display() if l.budget_band else "",
                      l.assigned_to.get_full_name() if l.assigned_to else "") for l in rows])
    if kind == "sources":
        return _csv(f"leads-by-source-{stamp}.csv", ["Source", "Leads", "Won", "Lost", "Conversion %"],
                    [(r["source"], r["leads"], r["won"], r["lost"], r["conversion"]) for r in source_rows(start)])
    if kind == "revenue":
        return _csv(f"revenue-by-month-{stamp}.csv", ["Month", "Payments received (INR)"],
                    [(label, f"{amount:.2f}") for label, amount in revenue_by_month(months)])
    if kind == "outstanding":
        return _csv(f"outstanding-{stamp}.csv", ["Invoice", "Date", "Client", "Project", "Due date", "Total (INR)", "Balance (INR)", "Days overdue"],
                    [(r["invoice"].number, r["invoice"].date.strftime("%d-%m-%Y"), r["invoice"].client_name, r["invoice"].project.name,
                      r["invoice"].due_date.strftime("%d-%m-%Y") if r["invoice"].due_date else "", r["invoice"].total, r["balance"],
                      r["days_overdue"]) for r in outstanding()])
    if kind == "payments":
        return _csv(f"payments-{stamp}.csv", ["Date", "Invoice", "Client", "Amount (INR)", "Mode", "Reference"],
                    [(p.date.strftime("%d-%m-%Y"), p.invoice.number, p.invoice.client_name, p.amount, p.get_mode_display(), p.reference)
                     for p in payments(start)])
    return None
