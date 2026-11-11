from django import forms
from django.utils import timezone

from crm.models import Lead
from studio.forms import DATE, StyledMixin
from studio.models import ClientProject

from .models import CatalogueItem, Payment, Vendor


class VendorForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "category", "contact_person", "phone", "email", "city", "gstin", "payment_terms", "notes", "is_active"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_gstin(self):
        import re
        v = (self.cleaned_data.get("gstin") or "").strip().upper()
        if v and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", v):
            raise forms.ValidationError("Enter a valid 15-character GSTIN or leave it blank.")
        return v


class CatalogueItemForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = CatalogueItem
        fields = ["name", "category", "vendor", "unit", "rate", "gst_percent", "hsn_code", "description", "is_active"]
        labels = {"rate": "Rate (₹)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = Vendor.objects.filter(is_active=True)
        self._style()

    def clean_rate(self):
        v = self.cleaned_data["rate"]
        if v < 0:
            raise forms.ValidationError("Rate can't be negative.")
        return v

    def clean_gst_percent(self):
        v = self.cleaned_data["gst_percent"]
        if v not in (0, 5, 12, 18, 28):
            raise forms.ValidationError("Use a GST slab: 0, 5, 12, 18 or 28%.")
        return v


class NewQuotationForm(StyledMixin, forms.Form):
    project = forms.ModelChoiceField(queryset=ClientProject.objects.exclude(stage="completed"), required=False,
                                     label="Client project", empty_label="— Choose a project —")
    lead = forms.ModelChoiceField(queryset=Lead.objects.exclude(stage__in=["won", "lost"]), required=False,
                                  label="…or a lead (before they become a client)", empty_label="— Choose a lead —")
    title = forms.CharField(max_length=140, initial="Interior design & execution")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].label_from_instance = lambda p: f"{p.code} · {p.name}"
        self.fields["lead"].label_from_instance = lambda l: f"{l.name} · {l.get_stage_display()}"
        self._style()

    def clean(self):
        d = super().clean()
        if not d.get("project") and not d.get("lead"):
            raise forms.ValidationError("Choose a client project or a lead.")
        return d


class PaymentForm(StyledMixin, forms.Form):
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=1, label="Amount (₹)")
    date = forms.DateField(widget=DATE, initial=timezone.localdate)
    mode = forms.ChoiceField(choices=Payment.Mode.choices)
    reference = forms.CharField(max_length=80, required=False, label="Reference (UTR / UPI / cheque no.)")
    notes = forms.CharField(max_length=200, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
