from django import forms
from django.contrib.auth.models import User

from bookings.models import BlockedDate, WeeklyAvailability
from core.models import StudioSettings
from core.permissions import OWNER, TEAM
from core.validators import validate_image
from crm.models import Lead
from website.forms import clean_indian_mobile

from .models import ClientProject, DesignProposal, Milestone, ProjectDocument, ProjectSpace, Task

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


def team_users():
    return User.objects.filter(groups__name__in=[OWNER, TEAM]).distinct().order_by("first_name")


class StyledMixin:
    """Bootstrap classes + red borders on invalid fields."""

    def _style(self):
        for field in self.fields.values():
            w = field.widget
            # Formset rows show column headings instead of <label>s; keep fields named for screen readers.
            if field.label and not isinstance(w, forms.HiddenInput):
                w.attrs.setdefault("aria-label", str(field.label))
            if isinstance(w, (forms.CheckboxInput,)):
                w.attrs.setdefault("class", "form-check-input")
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            elif not isinstance(w, forms.HiddenInput):
                w.attrs.setdefault("class", "form-control")

    def full_clean(self):
        super().full_clean()
        for name in getattr(self, "_errors", None) or {}:
            if name in self.fields:
                w = self.fields[name].widget
                w.attrs["class"] = (w.attrs.get("class", "") + " is-invalid").strip()


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        if self.required and not files:
            raise forms.ValidationError("Please add at least one image.")
        if len(files) > 12:
            raise forms.ValidationError("Please upload at most 12 images at a time.")
        for f in files:
            validate_image(f)
        return files


# ---------------------------------------------------------------- leads
class LeadForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["name", "mobile", "email", "city", "source", "stage", "property_type", "budget_band",
                  "style_preference", "follow_up_date", "assigned_to", "message", "notes"]
        widgets = {"follow_up_date": DATE, "message": forms.Textarea(attrs={"rows": 3}),
                   "notes": forms.Textarea(attrs={"rows": 3})}
        labels = {"message": "Requirement", "notes": "Internal notes"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = team_users()
        self.fields["assigned_to"].label_from_instance = lambda u: u.get_full_name() or u.username
        self._style()

    def clean_mobile(self):
        return clean_indian_mobile(self.cleaned_data.get("mobile"))


class NoteForm(forms.Form):
    text = forms.CharField(max_length=300, widget=forms.TextInput(
        attrs={"class": "form-control", "placeholder": "Add a note, e.g. “Called, will visit site on Sunday”"}))


# ---------------------------------------------------------------- bookings
class AvailabilityForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = WeeklyAvailability
        fields = ["weekday", "start_time", "end_time", "slot_minutes", "is_active"]
        widgets = {"start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
                   "end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean(self):
        d = super().clean()
        if d.get("start_time") and d.get("end_time") and d["start_time"] >= d["end_time"]:
            raise forms.ValidationError("End time must be after start time.")
        if d.get("slot_minutes") and not 15 <= d["slot_minutes"] <= 240:
            self.add_error("slot_minutes", "Use 15–240 minutes.")
        return d


AvailabilityFormSet = forms.modelformset_factory(WeeklyAvailability, form=AvailabilityForm, extra=1, can_delete=True)


class BlockedDateForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = BlockedDate
        fields = ["date", "reason"]
        widgets = {"date": DATE}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


# ---------------------------------------------------------------- projects
class ProjectForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = ClientProject
        fields = ["name", "client_name", "client_mobile", "client_email", "designer", "stage", "property_type",
                  "site_address", "area_sqft", "start_date", "target_date", "budget", "actual_cost", "notes"]
        widgets = {"start_date": DATE, "target_date": DATE, "notes": forms.Textarea(attrs={"rows": 3})}
        labels = {"budget": "Budget (₹)", "actual_cost": "Spent so far (₹)", "area_sqft": "Area (sq ft)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["designer"].queryset = team_users()
        self.fields["designer"].label_from_instance = lambda u: u.get_full_name() or u.username
        self._style()

    def clean(self):
        d = super().clean()
        if d.get("start_date") and d.get("target_date") and d["target_date"] < d["start_date"]:
            self.add_error("target_date", "Target date must be after the start date.")
        return d


class TaskForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "assigned_to", "due_date", "priority"]
        widgets = {"due_date": DATE, "title": forms.TextInput(attrs={"placeholder": "What needs to be done?"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = team_users()
        self.fields["assigned_to"].label_from_instance = lambda u: u.get_full_name() or u.username
        self._style()


class MilestoneForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ["title", "due_date"]
        widgets = {"due_date": DATE}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class SpaceForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = ProjectSpace
        fields = ["name", "area_sqft", "scope"]
        labels = {"area_sqft": "Area (sq ft)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class ProposalForm(StyledMixin, forms.ModelForm):
    images = MultipleImageField(label="Design images", required=True)
    share = forms.BooleanField(required=False, initial=True, label="Share with the client now")

    class Meta:
        model = DesignProposal
        fields = ["title", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3, "placeholder": "What changed in this version?"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class SiteUpdateForm(StyledMixin, forms.Form):
    message = forms.CharField(max_length=2000, widget=forms.Textarea(
        attrs={"rows": 3, "placeholder": "e.g. False ceiling framing done in the living room."}))
    photos = MultipleImageField(required=False, label="Site photos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class DocumentForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = ProjectDocument
        fields = ["title", "kind", "file", "visible_to_client"]
        widgets = {"file": forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png,.webp,.txt"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


# ---------------------------------------------------------------- studio settings (owner)
class StudioSettingsForm(StyledMixin, forms.ModelForm):
    schedule_text = forms.CharField(
        label="Payment schedule", widget=forms.Textarea(attrs={"rows": 4}),
        help_text="One milestone per line: Label | percent. Must add up to 100.")

    class Meta:
        model = StudioSettings
        fields = ["name", "tagline", "logo", "accent_color", "secondary_color", "dark_color",
                  "city", "address", "phone", "whatsapp", "email", "map_embed_query", "instagram", "working_hours",
                  "founded_year", "hero_title", "hero_subtitle", "about_text",
                  "legal_name", "gstin", "state_name", "default_gst_percent", "quotation_terms", "bank_details",
                  "rate_essential", "rate_premium", "rate_luxury", "easy_payment_text",
                  "module_website", "module_cms", "module_portal", "module_erp", "module_automation", "module_ai",
                  "show_locked_teasers", "module_tour360"]
        widgets = {
            "accent_color": forms.TextInput(attrs={"type": "color"}),
            "secondary_color": forms.TextInput(attrs={"type": "color"}),
            "dark_color": forms.TextInput(attrs={"type": "color"}),
            "address": forms.Textarea(attrs={"rows": 2}),
            "about_text": forms.Textarea(attrs={"rows": 4}),
            "hero_subtitle": forms.Textarea(attrs={"rows": 2}),
            "quotation_terms": forms.Textarea(attrs={"rows": 3}),
            "bank_details": forms.Textarea(attrs={"rows": 2}),
            "easy_payment_text": forms.Textarea(attrs={"rows": 3}),
            "logo": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and not self.is_bound:
            self.initial["schedule_text"] = "\n".join(
                f"{row['label']} | {row['percent']}" for row in (self.instance.payment_schedule or []))
        for name in ("accent_color", "secondary_color", "dark_color"):
            self.fields[name].widget.attrs["class"] = "form-control form-control-color"
        self._style()

    def clean_logo(self):
        f = self.cleaned_data.get("logo")
        if f and hasattr(f, "content_type"):  # a new upload
            from core.validators import validate_image
            validate_image(f)
        return f

    def clean_whatsapp(self):
        digits = "".join(c for c in self.cleaned_data.get("whatsapp", "") if c.isdigit())
        if len(digits) == 10:
            digits = "91" + digits
        if not 11 <= len(digits) <= 15:
            raise forms.ValidationError("Enter the WhatsApp number with country code, e.g. 919827000000.")
        return digits

    def clean_gstin(self):
        import re
        v = (self.cleaned_data.get("gstin") or "").strip().upper()
        if v and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", v):
            raise forms.ValidationError("This doesn't look like a valid 15-character GSTIN.")
        return v

    def clean_schedule_text(self):
        rows = []
        for line in self.cleaned_data["schedule_text"].splitlines():
            if not line.strip():
                continue
            label, sep, pct = line.rpartition("|")
            try:
                pct = int(pct.strip().rstrip("%"))
            except ValueError:
                raise forms.ValidationError(f"“{line.strip()}” — use the format Label | percent.")
            if not sep or not label.strip() or pct <= 0:
                raise forms.ValidationError(f"“{line.strip()}” — use the format Label | percent.")
            rows.append({"label": label.strip()[:60], "percent": pct})
        if not rows:
            raise forms.ValidationError("Add at least one payment milestone.")
        if sum(r["percent"] for r in rows) != 100:
            raise forms.ValidationError(f"The percentages add up to {sum(r['percent'] for r in rows)}%; they must add up to 100%.")
        return rows

    def clean(self):
        d = super().clean()
        rates = [d.get("rate_essential"), d.get("rate_premium"), d.get("rate_luxury")]
        if all(rates) and not rates[0] <= rates[1] <= rates[2]:
            self.add_error("rate_luxury", "Rates should increase from Essential to Premium to Luxury.")
        return d

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.payment_schedule = self.cleaned_data["schedule_text"]
        if commit:
            obj.save()
        return obj


class TeamMemberForm(StyledMixin, forms.Form):
    first_name = forms.CharField(label="First name", max_length=60)
    last_name = forms.CharField(label="Last name", max_length=60, required=False)
    username = forms.SlugField(label="Login username", max_length=40, help_text="Letters, numbers, - and _ only.")
    email = forms.EmailField(required=False)
    role = forms.ChoiceField(choices=[(TEAM, "Team member"), (OWNER, "Owner")], initial=TEAM)
    password = forms.CharField(widget=forms.PasswordInput(render_value=False), min_length=8,
                               help_text="At least 8 characters. Share it privately with the team member.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_username(self):
        u = self.cleaned_data["username"].lower()
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("This username is already taken.")
        return u

    def clean_password(self):
        from django.contrib.auth.password_validation import validate_password
        pw = self.cleaned_data["password"]
        validate_password(pw)
        return pw
