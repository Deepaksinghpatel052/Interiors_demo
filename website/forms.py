import re

from django import forms

from crm.models import Lead

from .models import Style


def clean_indian_mobile(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise forms.ValidationError("Please enter a valid 10-digit Indian mobile number.")
    return digits


class EnquiryForm(forms.ModelForm):
    """Contact / consultation request. Creates a Lead."""

    website = forms.CharField(required=False, widget=forms.HiddenInput)  # honeypot
    style_preference = forms.ChoiceField(
        required=False, choices=[("", "Not sure yet")] + list(Style.choices), label="Preferred style")

    class Meta:
        model = Lead
        fields = ["name", "mobile", "email", "property_type", "budget_band", "style_preference", "message"]
        labels = {"mobile": "Mobile number", "message": "Tell us about your space"}
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Your full name"}),
            "mobile": forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "tel",
                                             "placeholder": "10-digit mobile", "maxlength": 14}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "Optional"}),
            "message": forms.Textarea(attrs={"rows": 4, "maxlength": 1500,
                                             "placeholder": "Rooms, timeline, anything you have in mind"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property_type"].required = False
        self.fields["budget_band"].required = False
        self.fields["property_type"].choices = [("", "Select property")] + list(self.fields["property_type"].choices)[1:]
        self.fields["budget_band"].choices = [("", "Select budget")] + list(self.fields["budget_band"].choices)[1:]
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                w = self.fields[name].widget
                w.attrs["class"] = (w.attrs.get("class", "") + " is-invalid").strip()

    def clean_mobile(self):
        return clean_indian_mobile(self.cleaned_data.get("mobile"))

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your name.")
        return name

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class EstimateLeadForm(forms.Form):
    """'Get an exact quote' from the estimator — just contact details."""

    name = forms.CharField(max_length=100, widget=forms.TextInput(
        attrs={"class": "form-control", "autocomplete": "name", "placeholder": "Your full name"}))
    mobile = forms.CharField(max_length=14, label="Mobile number", widget=forms.TextInput(
        attrs={"class": "form-control", "inputmode": "numeric", "autocomplete": "tel", "placeholder": "10-digit mobile"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(
        attrs={"class": "form-control", "autocomplete": "email", "placeholder": "Optional"}))
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                w = self.fields[name].widget
                w.attrs["class"] = (w.attrs.get("class", "") + " is-invalid").strip()

    def clean_mobile(self):
        return clean_indian_mobile(self.cleaned_data.get("mobile"))

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your name.")
        return name

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""
