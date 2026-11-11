from django import forms

from website.forms import clean_indian_mobile
from website.models import BudgetBand, PropertyType

from .models import Booking
from .slots import is_slot_available


class BookingForm(forms.Form):
    mode = forms.ChoiceField(choices=Booking.Mode.choices, initial=Booking.Mode.STUDIO, widget=forms.RadioSelect)
    date = forms.DateField(input_formats=["%Y-%m-%d"], widget=forms.HiddenInput,
                           error_messages={"required": "Please pick a date."})
    time = forms.TimeField(input_formats=["%H:%M"], widget=forms.HiddenInput,
                           error_messages={"required": "Please pick a time slot."})
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Your full name"}))
    mobile = forms.CharField(label="Mobile number", max_length=14, widget=forms.TextInput(
        attrs={"inputmode": "numeric", "autocomplete": "tel", "placeholder": "10-digit mobile"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "Optional"}))
    property_type = forms.ChoiceField(required=False, choices=[("", "Select property")] + list(PropertyType.choices))
    budget_band = forms.ChoiceField(required=False, choices=[("", "Select budget")] + list(BudgetBand.choices))
    site_address = forms.CharField(required=False, max_length=240, label="Site address",
                                   widget=forms.TextInput(attrs={"placeholder": "Flat / house, society, area"}))
    notes = forms.CharField(required=False, max_length=1500, label="Anything we should know?",
                            widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Rooms, timeline, references you like"}))
    style = forms.CharField(required=False, widget=forms.HiddenInput)
    website = forms.CharField(required=False, widget=forms.HiddenInput)  # honeypot

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.HiddenInput, forms.RadioSelect)):
                continue
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
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your name.")
        return name

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""

    def clean(self):
        data = super().clean()
        if data.get("mode") == Booking.Mode.SITE and not data.get("site_address"):
            self.add_error("site_address", "Please share the site address for a site visit.")
        day, t = data.get("date"), data.get("time")
        if day and t and not is_slot_available(day, t):
            raise forms.ValidationError("Sorry, that slot is no longer available. Please pick another time.")
        return data
