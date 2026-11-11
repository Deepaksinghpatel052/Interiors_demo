from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

User = settings.AUTH_USER_MODEL
TWO = Decimal("0.01")


def money(v):
    return Decimal(v or 0).quantize(TWO, rounding=ROUND_HALF_UP)


def financial_year(d):
    """Indian FY label for a date: 05-11-2026 -> '2026-27'; 15-02-2027 -> '2026-27'."""
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


class Category(models.TextChoices):
    PLYWOOD = "plywood", "Plywood & boards"
    LAMINATE = "laminate", "Laminates & veneers"
    HARDWARE = "hardware", "Hardware & fittings"
    LIGHTING = "lighting", "Lighting & electrical"
    FABRIC = "fabric", "Fabrics & soft furnishings"
    STONE = "stone", "Stone, quartz & tiles"
    PAINT = "paint", "Paint & finishes"
    SANITARY = "sanitary", "Sanitary & bath"
    FURNITURE = "furniture", "Furniture & décor"
    SERVICES = "services", "Labour & services"
    OTHER = "other", "Other"


class Vendor(models.Model):
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=Category.choices)
    contact_person = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=60, blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True)
    payment_terms = models.CharField(max_length=120, blank=True, help_text="e.g. 50% advance, balance on delivery")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CatalogueItem(models.Model):
    class Unit(models.TextChoices):
        SQFT = "sqft", "sq ft"
        RFT = "rft", "rft"
        SQM = "sqm", "sq m"
        NOS = "nos", "nos"
        SET = "set", "set"
        SHEET = "sheet", "sheet"
        LTR = "ltr", "ltr"
        KG = "kg", "kg"
        JOB = "job", "job"
        LS = "ls", "LS"

    name = models.CharField(max_length=140)
    category = models.CharField(max_length=20, choices=Category.choices)
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.SET_NULL, related_name="items")
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.SQFT)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percent = models.DecimalField("GST %", max_digits=5, decimal_places=2, default=18)
    hsn_code = models.CharField("HSN/SAC", max_length=10, blank=True)
    description = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"


# ------------------------------------------------------------------------------ quotations
class Quotation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent to client"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        SUPERSEDED = "superseded", "Superseded"

    number = models.CharField(max_length=30, editable=False)
    version = models.PositiveIntegerField(default=1)
    project = models.ForeignKey("studio.ClientProject", null=True, blank=True, on_delete=models.CASCADE, related_name="quotations")
    lead = models.ForeignKey("crm.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="quotations")
    client_name = models.CharField(max_length=100)
    client_mobile = models.CharField(max_length=15, blank=True)
    client_address = models.CharField(max_length=240, blank=True)
    client_gstin = models.CharField("Client GSTIN", max_length=15, blank=True)
    title = models.CharField(max_length=140, default="Interior design & execution")
    date = models.DateField(default=timezone.localdate)
    valid_until = models.DateField(null=True, blank=True)
    inter_state = models.BooleanField(default=False, help_text="Client outside the studio's state: charge IGST instead of CGST + SGST.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    # Cached totals (recalculated on every save of items)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxable_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    round_off = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    sent_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [models.UniqueConstraint(fields=["number", "version"], name="unique_quotation_version")]

    def __str__(self):
        return self.display_number

    @property
    def display_number(self):
        return f"{self.number}" + (f" (v{self.version})" if self.version > 1 else "")

    def get_absolute_url(self):
        return reverse("finance:quotation_detail", args=[self.pk])

    @property
    def editable(self):
        return self.status == self.Status.DRAFT

    @property
    def cgst(self):
        return Decimal(0) if self.inter_state else money(self.gst_total / 2)

    @property
    def sgst(self):
        return Decimal(0) if self.inter_state else money(self.gst_total - self.cgst)

    @property
    def igst(self):
        return self.gst_total if self.inter_state else Decimal(0)

    def items(self):
        return QuotationItem.objects.filter(room__quotation=self)

    def gst_breakdown(self):
        """[(rate, taxable, gst)] grouped by GST rate — needed on GST invoices."""
        groups = {}
        for it in self.items():
            g = groups.setdefault(it.gst_percent, [Decimal(0), Decimal(0)])
            g[0] += it.taxable
            g[1] += it.gst_amount
        return [(rate, money(t), money(g)) for rate, (t, g) in sorted(groups.items())]

    def recalculate(self, save=True):
        sub = disc = taxable = gst = Decimal(0)
        for it in self.items():
            sub += it.amount
            disc += it.discount_amount
            taxable += it.taxable
            gst += it.gst_amount
        self.subtotal, self.discount_total = money(sub), money(disc)
        self.taxable_total, self.gst_total = money(taxable), money(gst)
        exact = self.taxable_total + self.gst_total
        self.grand_total = exact.quantize(Decimal(1), rounding=ROUND_HALF_UP)
        self.round_off = money(self.grand_total - exact)
        if save:
            self.save(update_fields=["subtotal", "discount_total", "taxable_total", "gst_total",
                                     "grand_total", "round_off", "updated_at"])


class QuotationRoom(models.Model):
    quotation = models.ForeignKey(Quotation, related_name="rooms", on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def total(self):
        return money(sum((it.taxable for it in self.items.all()), Decimal(0)))


class QuotationItem(models.Model):
    room = models.ForeignKey(QuotationRoom, related_name="items", on_delete=models.CASCADE)
    catalogue_item = models.ForeignKey(CatalogueItem, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.CharField(max_length=240)
    hsn_code = models.CharField(max_length=10, blank=True)
    unit = models.CharField(max_length=10, choices=CatalogueItem.Unit.choices, default=CatalogueItem.Unit.SQFT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    @property
    def amount(self):
        return money(self.quantity * self.rate)

    @property
    def discount_amount(self):
        return money(self.amount * self.discount_percent / 100)

    @property
    def taxable(self):
        return money(self.amount - self.discount_amount)

    @property
    def gst_amount(self):
        return money(self.taxable * self.gst_percent / 100)

    @property
    def total(self):
        return money(self.taxable + self.gst_amount)


# ------------------------------------------------------------------------------ payments & invoices
class PaymentScheduleItem(models.Model):
    project = models.ForeignKey("studio.ClientProject", related_name="schedule", on_delete=models.CASCADE)
    quotation = models.ForeignKey(Quotation, related_name="schedule", on_delete=models.CASCADE)
    label = models.CharField(max_length=60)
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.label} ({self.percent}%)"

    @property
    def invoice(self):
        return self.invoices.exclude(status=Invoice.Status.CANCELLED).first()

    @property
    def state(self):
        inv = self.invoice
        if not inv:
            return "due" if self.due_date and self.due_date <= timezone.localdate() else "upcoming"
        return inv.status


class Invoice(models.Model):
    class Status(models.TextChoices):
        ISSUED = "issued", "Issued"
        PARTIAL = "partial", "Partly paid"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30, unique=True, editable=False)
    financial_year = models.CharField(max_length=7, editable=False)
    sequence = models.PositiveIntegerField(editable=False)
    project = models.ForeignKey("studio.ClientProject", related_name="invoices", on_delete=models.CASCADE)
    schedule_item = models.ForeignKey(PaymentScheduleItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    description = models.CharField(max_length=200)
    date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    client_name = models.CharField(max_length=100)
    client_address = models.CharField(max_length=240, blank=True)
    client_gstin = models.CharField(max_length=15, blank=True)
    inter_state = models.BooleanField(default=False)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ISSUED)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-sequence"]
        constraints = [models.UniqueConstraint(fields=["financial_year", "sequence"], name="unique_invoice_sequence")]

    def __str__(self):
        return self.number

    def get_absolute_url(self):
        return reverse("finance:invoice_detail", args=[self.pk])

    @property
    def cgst(self):
        return Decimal(0) if self.inter_state else money(self.gst_amount / 2)

    @property
    def sgst(self):
        return Decimal(0) if self.inter_state else money(self.gst_amount - self.cgst)

    @property
    def igst(self):
        return self.gst_amount if self.inter_state else Decimal(0)

    @property
    def paid(self):
        return money(sum((p.amount for p in self.payments.all()), Decimal(0)))

    @property
    def balance(self):
        return money(self.total - self.paid) if self.status != self.Status.CANCELLED else Decimal(0)

    @property
    def is_overdue(self):
        return self.status in (self.Status.ISSUED, self.Status.PARTIAL) and self.due_date and self.due_date < timezone.localdate()

    def refresh_status(self):
        if self.status == self.Status.CANCELLED:
            return
        paid = self.paid
        self.status = self.Status.PAID if paid >= self.total else (self.Status.PARTIAL if paid > 0 else self.Status.ISSUED)
        self.save(update_fields=["status"])


class Payment(models.Model):
    class Mode(models.TextChoices):
        UPI = "upi", "UPI"
        BANK = "bank_transfer", "Bank transfer (NEFT/RTGS/IMPS)"
        CASH = "cash", "Cash"
        CHEQUE = "cheque", "Cheque"

    invoice = models.ForeignKey(Invoice, related_name="payments", on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.UPI)
    reference = models.CharField(max_length=80, blank=True, help_text="UTR / UPI ref / cheque no.")
    notes = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.amount} via {self.get_mode_display()}"
