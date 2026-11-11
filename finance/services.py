"""Quotation, invoice and payment rules. Views and the seed call these; tests cover them."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import StudioSettings
from crm.models import LeadActivity

from .models import (CatalogueItem, Invoice, Payment, PaymentScheduleItem, Quotation, QuotationItem, QuotationRoom,
                     financial_year, money)

MAX_ROOMS, MAX_ITEMS = 30, 400


class FinanceError(ValueError):
    pass


# ------------------------------------------------------------------------------ numbering
def next_quotation_number(on_date=None):
    fy = financial_year(on_date or timezone.localdate())
    prefix = f"QT/{fy}/"
    existing = Quotation.objects.filter(number__startswith=prefix).values_list("number", flat=True).distinct()
    seq = max((int(n.rsplit("/", 1)[-1]) for n in existing), default=0) + 1
    return f"{prefix}{seq:03d}"


def _next_invoice_sequence(fy):
    last = Invoice.objects.filter(financial_year=fy).order_by("-sequence").values_list("sequence", flat=True).first()
    return (last or 0) + 1


# ------------------------------------------------------------------------------ quotations
def schedule_split(total):
    """[(label, percent, amount)] from the studio's payment milestones; whole rupees, last row takes the remainder."""
    schedule = StudioSettings.load().payment_schedule or [{"label": "Full payment", "percent": 100}]
    rows, allotted, total = [], Decimal(0), money(total)
    for i, row in enumerate(schedule):
        pct = Decimal(str(row["percent"]))
        amount = (total - allotted) if i == len(schedule) - 1 else money(total * pct / 100).quantize(Decimal(1))
        allotted += amount
        rows.append((row["label"][:60], pct, money(amount)))
    return rows


def create_quotation(*, project=None, lead=None, user=None, title=None):
    if not project and not lead:
        raise FinanceError("A quotation needs a client project or a lead.")
    s = StudioSettings.load()
    today = timezone.localdate()
    q = Quotation(
        number=next_quotation_number(today), project=project, lead=lead or (project.lead if project else None),
        client_name=project.client_name if project else lead.name,
        client_mobile=project.client_mobile if project else lead.mobile,
        client_address=(project.site_address if project else lead.city) or "",
        title=title or "Interior design & execution", date=today, valid_until=today + timedelta(days=30),
        terms=s.quotation_terms, created_by=user)
    q.save()
    return q


def _dec(value, field, minimum=Decimal(0), maximum=Decimal("10000000")):
    try:
        d = Decimal(str(value).strip() or "0")
    except (InvalidOperation, ValueError):
        raise FinanceError(f"{field} must be a number.")
    if not d.is_finite() or d < minimum or d > maximum:
        raise FinanceError(f"{field} must be between {minimum} and {maximum}.")
    return d


@transaction.atomic
def save_builder(q: Quotation, data: dict):
    """Replace the quotation's rooms/items from the builder payload. Totals are recalculated server-side."""
    if not q.editable:
        raise FinanceError("Only draft quotations can be edited. Create a revision instead.")
    rooms = data.get("rooms") or []
    if len(rooms) > MAX_ROOMS or sum(len(r.get("items") or []) for r in rooms) > MAX_ITEMS:
        raise FinanceError("This quotation is too large.")
    q.title = (data.get("title") or q.title)[:140]
    q.notes = (data.get("notes") or "")[:2000]
    q.terms = (data.get("terms") or "")[:3000]
    q.client_address = (data.get("client_address") or q.client_address)[:240]
    q.client_gstin = (data.get("client_gstin") or "").strip().upper()[:15]
    q.inter_state = bool(data.get("inter_state"))
    if data.get("valid_until"):
        try:
            from datetime import date
            q.valid_until = date.fromisoformat(str(data["valid_until"])[:10])
        except ValueError:
            raise FinanceError("Valid-until date is not valid.")
    q.save()
    QuotationRoom.objects.filter(quotation=q).delete()
    catalogue = {c.pk: c for c in CatalogueItem.objects.filter(
        pk__in=[it.get("catalogue_id") for r in rooms for it in (r.get("items") or []) if it.get("catalogue_id")])}
    units = set(CatalogueItem.Unit.values)
    for ri, r in enumerate(rooms):
        name = (r.get("name") or "").strip()[:80] or f"Room {ri + 1}"
        room = QuotationRoom.objects.create(quotation=q, name=name, order=ri)
        for ii, it in enumerate(r.get("items") or []):
            desc = (it.get("description") or "").strip()[:240]
            if not desc:
                raise FinanceError(f"Every item in “{name}” needs a description.")
            unit = it.get("unit") if it.get("unit") in units else CatalogueItem.Unit.NOS
            cat = catalogue.get(int(it["catalogue_id"])) if str(it.get("catalogue_id") or "").isdigit() else None
            QuotationItem.objects.create(
                room=room, catalogue_item=cat, description=desc, unit=unit,
                hsn_code=(it.get("hsn_code") or (cat.hsn_code if cat else ""))[:10],
                quantity=_dec(it.get("quantity", 1), "Quantity", Decimal("0.01"), Decimal("100000")),
                rate=_dec(it.get("rate", 0), "Rate"),
                discount_percent=_dec(it.get("discount_percent", 0), "Discount", Decimal(0), Decimal(100)),
                gst_percent=_dec(it.get("gst_percent", 18), "GST", Decimal(0), Decimal(28)),
                order=ii)
    q.recalculate()
    return q


def send_quotation(q: Quotation, user=None):
    if q.status != Quotation.Status.DRAFT:
        raise FinanceError("Only draft quotations can be sent.")
    if not q.items().exists():
        raise FinanceError("Add at least one item before sending.")
    q.status, q.sent_at = Quotation.Status.SENT, timezone.now()
    q.save(update_fields=["status", "sent_at", "updated_at"])
    try:
        from automations.engine import quotation_sent
        quotation_sent(q)
    except Exception:  # never block sending a quotation
        import logging
        logging.getLogger(__name__).exception("quotation automation failed")
    if q.lead_id:
        LeadActivity.objects.create(lead_id=q.lead_id, user=user,
                                    text=f"Quotation {q.display_number} sent · total ₹{q.grand_total:,.0f}")
        if q.lead.stage in ("new", "contacted", "consultation", "site_visit"):
            q.lead.stage = "proposal"
            q.lead.save(update_fields=["stage", "updated_at"])
    return q


@transaction.atomic
def revise_quotation(q: Quotation, user=None):
    """Copy a sent/rejected quotation into a new draft version; the old one is superseded."""
    if q.status in (Quotation.Status.DRAFT, Quotation.Status.ACCEPTED):
        raise FinanceError("Drafts can be edited directly, and accepted quotations can't be revised.")
    latest = Quotation.objects.filter(number=q.number).order_by("-version").first()
    new = Quotation.objects.get(pk=q.pk)
    new.pk, new.version, new.status = None, latest.version + 1, Quotation.Status.DRAFT
    new.sent_at = new.decided_at = None
    new.date, new.created_by = timezone.localdate(), user
    new.valid_until = new.date + timedelta(days=30)
    new.save()
    for room in q.rooms.all():
        items = list(room.items.all())
        room.pk, room.quotation = None, new
        room.save()
        for it in items:
            it.pk, it.room = None, room
            it.save()
    new.recalculate()
    Quotation.objects.filter(number=q.number).exclude(pk=new.pk).exclude(
        status=Quotation.Status.ACCEPTED).update(status=Quotation.Status.SUPERSEDED)
    return new


@transaction.atomic
def accept_quotation(q: Quotation, user=None):
    """Mark accepted and create the payment schedule from the studio's milestones."""
    if q.status != Quotation.Status.SENT:
        raise FinanceError("Only a quotation that was sent to the client can be accepted.")
    if not q.project_id:
        raise FinanceError("Convert this lead into a client project before accepting the quotation.")
    if PaymentScheduleItem.objects.filter(project=q.project).exists():
        raise FinanceError("This project already has an accepted quotation and payment schedule.")
    q.status, q.decided_at = Quotation.Status.ACCEPTED, timezone.now()
    q.save(update_fields=["status", "decided_at", "updated_at"])
    Quotation.objects.filter(number=q.number).exclude(pk=q.pk).update(status=Quotation.Status.SUPERSEDED)

    items = [PaymentScheduleItem.objects.create(
                 project=q.project, quotation=q, label=label, percent=pct, amount=amount, order=i,
                 due_date=timezone.localdate() if i == 0 else None)
             for i, (label, pct, amount) in enumerate(schedule_split(q.grand_total))]
    project = q.project
    if not project.budget:
        project.budget = q.grand_total
        project.save(update_fields=["budget", "updated_at"])
    if q.lead_id:
        LeadActivity.objects.create(lead_id=q.lead_id, user=user, text=f"Quotation {q.display_number} accepted")
    return items


def reject_quotation(q: Quotation, user=None):
    if q.status != Quotation.Status.SENT:
        raise FinanceError("Only a sent quotation can be marked rejected.")
    q.status, q.decided_at = Quotation.Status.REJECTED, timezone.now()
    q.save(update_fields=["status", "decided_at", "updated_at"])
    return q


# ------------------------------------------------------------------------------ invoices & payments
def raise_invoice(item: PaymentScheduleItem, user=None, on_date=None, due_days=7):
    if item.invoice:
        raise FinanceError("An invoice already exists for this milestone.")
    q = item.quotation
    on_date = on_date or timezone.localdate()
    total = money(item.amount)
    base = q.taxable_total + q.gst_total
    taxable = money(total * q.taxable_total / base) if base else total
    fy = financial_year(on_date)
    project = item.project
    for _ in range(5):  # retry if two invoices are raised at the same moment
        seq = _next_invoice_sequence(fy)
        try:
            with transaction.atomic():
                inv = Invoice.objects.create(
                    number=f"INV/{fy}/{seq:04d}", financial_year=fy, sequence=seq, project=project,
                    schedule_item=item, description=f"{item.label} ({item.percent:g}% of {q.display_number})",
                    date=on_date, due_date=on_date + timedelta(days=due_days),
                    client_name=q.client_name, client_address=q.client_address, client_gstin=q.client_gstin,
                    inter_state=q.inter_state, taxable_amount=taxable, gst_amount=total - taxable, total=total,
                    created_by=user)
            break
        except IntegrityError:
            continue
    else:
        raise FinanceError("Could not allocate an invoice number. Please try again.")
    if not item.due_date:
        item.due_date = inv.due_date
        item.save(update_fields=["due_date"])
    return inv


@transaction.atomic
def record_payment(invoice: Invoice, *, amount, mode, on_date=None, reference="", notes="", user=None):
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status == Invoice.Status.CANCELLED:
        raise FinanceError("This invoice is cancelled.")
    amount = money(_dec(amount, "Amount", Decimal("1")))
    if amount > invoice.balance:
        raise FinanceError(f"Amount is more than the balance due (₹{invoice.balance:,.2f}).")
    if mode not in Payment.Mode.values:
        raise FinanceError("Choose a payment mode.")
    on_date = on_date or timezone.localdate()
    if on_date > timezone.localdate():
        raise FinanceError("Payment date can't be in the future.")
    p = Payment.objects.create(invoice=invoice, amount=amount, mode=mode, date=on_date,
                               reference=reference[:80], notes=notes[:200], recorded_by=user)
    invoice.refresh_status()
    return p


# ------------------------------------------------------------------------------ amount in words
_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
         "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n):
    return _ONES[n] if n < 20 else (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else ""))


def _three(n):
    h, r = divmod(n, 100)
    return ((_ONES[h] + " Hundred" + (" " if r else "")) if h else "") + (_two(r) if r else "")


def amount_in_words(value):
    """1,25,450.50 -> 'Rupees One Lakh Twenty Five Thousand Four Hundred Fifty and Fifty Paise Only'."""
    value = money(value)
    rupees, paise = int(value), int(round((value - int(value)) * 100))
    if rupees == 0 and paise == 0:
        return "Rupees Zero Only"
    parts = []
    crore, rest = divmod(rupees, 10_000_000)
    lakh, rest = divmod(rest, 100_000)
    thousand, rest = divmod(rest, 1000)
    if crore:
        parts.append(amount_in_words_int(crore) + " Crore")
    if lakh:
        parts.append(_two(lakh) + " Lakh")
    if thousand:
        parts.append(_two(thousand) + " Thousand")
    if rest:
        parts.append(_three(rest))
    words = "Rupees " + " ".join(parts) if parts else "Rupees Zero"
    if paise:
        words += f" and {_two(paise)} Paise"
    return words + " Only"


def amount_in_words_int(n):
    """Whole number in Indian words, used for crores (which can exceed 99)."""
    if n < 1000:
        return _three(n)
    return amount_in_words(n).replace("Rupees ", "").replace(" Only", "")
