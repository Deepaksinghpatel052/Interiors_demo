import json

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.permissions import is_owner, owner_required, team_required

from . import pdf, services
from .forms import CatalogueItemForm, NewQuotationForm, PaymentForm, VendorForm
from .models import (CatalogueItem, Category, Invoice, Payment, PaymentScheduleItem, Quotation, Vendor)
from .services import FinanceError


def _err(request, e):
    messages.error(request, str(e))


# ============================================================================ quotations
@team_required
def quotation_list(request):
    status = request.GET.get("status", "")
    qs = Quotation.objects.select_related("project", "lead")
    if status in Quotation.Status.values:
        qs = qs.filter(status=status)
    counts = dict(Quotation.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    return render(request, "finance/quotations.html", {
        "quotations": qs[:200], "status": status,
        "statuses": [(v, l, counts.get(v, 0)) for v, l in Quotation.Status.choices],
        "pipeline": Quotation.objects.filter(status=Quotation.Status.SENT).aggregate(t=Sum("grand_total"))["t"] or 0,
        "won": Quotation.objects.filter(status=Quotation.Status.ACCEPTED).aggregate(t=Sum("grand_total"))["t"] or 0,
    })


@team_required
def quotation_new(request):
    initial = {}
    if request.GET.get("project", "").isdigit():
        initial["project"] = request.GET["project"]
    if request.GET.get("lead", "").isdigit():
        initial["lead"] = request.GET["lead"]
    form = NewQuotationForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        q = services.create_quotation(project=d["project"], lead=d["lead"] if not d["project"] else None,
                                      user=request.user, title=d["title"])
        messages.success(request, f"Quotation {q.number} created. Add rooms and items below.")
        return redirect(q.get_absolute_url())
    return render(request, "finance/quotation_new.html", {"form": form})


def _builder_payload(q):
    return {
        "title": q.title, "notes": q.notes, "terms": q.terms, "client_address": q.client_address,
        "client_gstin": q.client_gstin, "inter_state": q.inter_state,
        "valid_until": q.valid_until.isoformat() if q.valid_until else "",
        "rooms": [{"name": r.name, "items": [{
            "catalogue_id": it.catalogue_item_id, "description": it.description, "hsn_code": it.hsn_code,
            "unit": it.unit, "quantity": str(it.quantity.normalize()), "rate": str(it.rate),
            "discount_percent": str(it.discount_percent.normalize()), "gst_percent": str(it.gst_percent.normalize()),
        } for it in r.items.all()]} for r in q.rooms.prefetch_related("items")],
    }


def _totals(q):
    return {"subtotal": str(q.subtotal), "discount_total": str(q.discount_total), "taxable_total": str(q.taxable_total),
            "cgst": str(q.cgst), "sgst": str(q.sgst), "igst": str(q.igst), "gst_total": str(q.gst_total),
            "round_off": str(q.round_off), "grand_total": str(q.grand_total)}


@team_required
def quotation_detail(request, pk):
    q = get_object_or_404(Quotation.objects.select_related("project", "lead", "created_by"), pk=pk)
    catalogue = [{"id": c.pk, "name": c.name, "category": c.get_category_display(), "unit": c.unit,
                  "rate": str(c.rate), "gst": str(c.gst_percent.normalize()), "hsn": c.hsn_code}
                 for c in CatalogueItem.objects.filter(is_active=True).order_by("category", "name")]
    return render(request, "finance/quotation_detail.html", {
        "q": q, "payload": _builder_payload(q), "catalogue": catalogue, "totals": _totals(q),
        "units": CatalogueItem.Unit.choices, "rooms": q.rooms.prefetch_related("items"),
        "versions": Quotation.objects.filter(number=q.number).order_by("version"),
        "schedule": q.schedule.all(), "can_decide": is_owner(request.user),
        "schedule_preview": services.schedule_split(q.grand_total),
    })


@team_required
@require_POST
def quotation_save(request, pk):
    q = get_object_or_404(Quotation, pk=pk)
    try:
        data = json.loads(request.body or "{}")
        services.save_builder(q, data)
    except (ValueError, TypeError) as e:
        return JsonResponse({"ok": False, "error": str(e) or "Invalid data"}, status=400)
    q.refresh_from_db()
    return JsonResponse({"ok": True, "totals": _totals(q)})


@team_required
@require_POST
def quotation_send(request, pk):
    q = get_object_or_404(Quotation, pk=pk)
    try:
        services.send_quotation(q, request.user)
        messages.success(request, f"{q.display_number} marked as sent. Share the PDF on WhatsApp or email.")
    except FinanceError as e:
        _err(request, e)
    return redirect(q.get_absolute_url())


@owner_required
@require_POST
def quotation_accept(request, pk):
    q = get_object_or_404(Quotation, pk=pk)
    try:
        items = services.accept_quotation(q, request.user)
        messages.success(request, f"Accepted. Payment schedule created with {len(items)} milestones.")
    except FinanceError as e:
        _err(request, e)
    return redirect(q.get_absolute_url())


@owner_required
@require_POST
def quotation_reject(request, pk):
    q = get_object_or_404(Quotation, pk=pk)
    try:
        services.reject_quotation(q, request.user)
        messages.info(request, f"{q.display_number} marked as rejected. You can create a revision.")
    except FinanceError as e:
        _err(request, e)
    return redirect(q.get_absolute_url())


@team_required
@require_POST
def quotation_revise(request, pk):
    q = get_object_or_404(Quotation, pk=pk)
    try:
        new = services.revise_quotation(q, request.user)
        messages.success(request, f"Revision v{new.version} created as a draft.")
        return redirect(new.get_absolute_url())
    except FinanceError as e:
        _err(request, e)
        return redirect(q.get_absolute_url())


@team_required
def quotation_pdf(request, pk):
    q = get_object_or_404(Quotation, pk=pk)
    return pdf.quotation_pdf(q, inline=request.GET.get("download") != "1")


# ============================================================================ invoices & payments
@team_required
def invoice_list(request):
    show = request.GET.get("show", "all")
    qs = Invoice.objects.select_related("project").prefetch_related("payments")
    if show == "outstanding":
        qs = qs.filter(status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL])
    invoices = list(qs[:300])
    outstanding = [i for i in Invoice.objects.filter(status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL]).prefetch_related("payments")]
    upcoming = (PaymentScheduleItem.objects.filter(invoices__isnull=True).select_related("project", "quotation")
                .order_by("due_date", "order")[:12])
    return render(request, "finance/invoices.html", {
        "invoices": invoices, "show": show, "upcoming": upcoming,
        "outstanding_total": sum((i.balance for i in outstanding), 0),
        "overdue_total": sum((i.balance for i in outstanding if i.is_overdue), 0),
        "received_total": Payment.objects.aggregate(t=Sum("amount"))["t"] or 0,
    })


@team_required
def invoice_detail(request, pk):
    inv = get_object_or_404(Invoice.objects.select_related("project", "schedule_item"), pk=pk)
    from core.models import StudioSettings
    from core.templatetags.studio import format_inr
    reminder = (f"Hi {inv.client_name}, a gentle reminder from {StudioSettings.load().name} for invoice {inv.number}. "
                f"Balance due: {format_inr(inv.balance)}. You can pay by UPI or bank transfer. Thank you!")
    return render(request, "finance/invoice_detail.html", {
        "inv": inv, "payments": inv.payments.select_related("recorded_by"), "reminder_text": reminder,
        "form": PaymentForm(initial={"amount": inv.balance}), "can_record": is_owner(request.user),
    })


@owner_required
@require_POST
def invoice_pay(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    form = PaymentForm(request.POST)
    if form.is_valid():
        d = form.cleaned_data
        try:
            services.record_payment(inv, amount=d["amount"], mode=d["mode"], on_date=d["date"],
                                    reference=d["reference"], notes=d["notes"], user=request.user)
            inv.refresh_from_db()
            messages.success(request, f"Payment of ₹{d['amount']:,.0f} recorded. Invoice is now {inv.get_status_display().lower()}.")
        except FinanceError as e:
            _err(request, e)
    else:
        _err(request, "Please enter a valid amount, date and mode.")
    return redirect(request.POST.get("next") or inv.get_absolute_url())


@owner_required
@require_POST
def invoice_cancel(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    if inv.payments.exists():
        _err(request, "This invoice has payments; it can't be cancelled.")
    else:
        inv.status = Invoice.Status.CANCELLED
        inv.save(update_fields=["status"])
        messages.info(request, f"{inv.number} cancelled. You can raise it again from the payment schedule.")
    return redirect(inv.get_absolute_url())


@team_required
def invoice_pdf(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    return pdf.invoice_pdf(inv, inline=request.GET.get("download") != "1")


@owner_required
@require_POST
def schedule_invoice(request, pk):
    item = get_object_or_404(PaymentScheduleItem, pk=pk)
    try:
        inv = services.raise_invoice(item, request.user)
        messages.success(request, f"Invoice {inv.number} raised for {item.label}.")
        return redirect(inv.get_absolute_url())
    except FinanceError as e:
        _err(request, e)
        return redirect(request.POST.get("next") or "finance:invoices")


# ============================================================================ vendors & catalogue
@team_required
def vendor_list(request):
    q, cat = request.GET.get("q", "").strip(), request.GET.get("category", "")
    vendors = Vendor.objects.annotate(item_count=Count("items"))
    if q:
        vendors = vendors.filter(Q(name__icontains=q) | Q(contact_person__icontains=q) | Q(city__icontains=q))
    if cat in Category.values:
        vendors = vendors.filter(category=cat)
    form = VendorForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            v = form.save()
            messages.success(request, f"Vendor “{v.name}” added.")
            return redirect("finance:vendors")
        messages.error(request, "Please fix the vendor details.")
    return render(request, "finance/vendors.html", {"vendors": vendors, "form": form, "q": q, "category": cat,
                                                    "categories": Category.choices})


@team_required
def vendor_edit(request, pk):
    v = get_object_or_404(Vendor, pk=pk)
    form = VendorForm(request.POST or None, instance=v)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vendor saved.")
        return redirect("finance:vendors")
    return render(request, "finance/simple_form.html", {"form": form, "title": f"Edit vendor · {v.name}",
                                                        "back": "finance:vendors", "obj": v, "delete_url": "finance:vendor_delete"})


@owner_required
@require_POST
def vendor_delete(request, pk):
    v = get_object_or_404(Vendor, pk=pk)
    v.delete()
    messages.success(request, "Vendor deleted. Its catalogue items were kept without a vendor.")
    return redirect("finance:vendors")


@team_required
def catalogue_list(request):
    q, cat = request.GET.get("q", "").strip(), request.GET.get("category", "")
    items = CatalogueItem.objects.select_related("vendor")
    if q:
        items = items.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(vendor__name__icontains=q))
    if cat in Category.values:
        items = items.filter(category=cat)
    form = CatalogueItemForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            it = form.save()
            messages.success(request, f"“{it.name}” added to the catalogue.")
            return redirect("finance:catalogue")
        messages.error(request, "Please fix the item details.")
    return render(request, "finance/catalogue.html", {"items": items, "form": form, "q": q, "category": cat,
                                                      "categories": Category.choices})


@team_required
def catalogue_edit(request, pk):
    it = get_object_or_404(CatalogueItem, pk=pk)
    form = CatalogueItemForm(request.POST or None, instance=it)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Item saved. New quotations will use the updated rate.")
        return redirect("finance:catalogue")
    return render(request, "finance/simple_form.html", {"form": form, "title": f"Edit item · {it.name}",
                                                        "back": "finance:catalogue", "obj": it, "delete_url": "finance:catalogue_delete"})


@owner_required
@require_POST
def catalogue_delete(request, pk):
    get_object_or_404(CatalogueItem, pk=pk).delete()
    messages.success(request, "Item deleted. Existing quotations keep their lines.")
    return redirect("finance:catalogue")
