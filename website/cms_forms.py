from django import forms
from django.utils.text import slugify

from core.models import StudioSettings
from core.validators import validate_image
from studio.forms import StyledMixin

from .models import (FAQ, BeforeAfter, PortfolioProject, ProjectRoom, ProjectSwatch, Service, Testimonial, Tour,
                     TourHotspot, TourRoom)


class Styled(StyledMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class HomepageForm(Styled, forms.ModelForm):
    class Meta:
        model = StudioSettings
        fields = ["tagline", "hero_title", "hero_subtitle", "about_text", "founded_year"]
        widgets = {"hero_subtitle": forms.Textarea(attrs={"rows": 2}), "about_text": forms.Textarea(attrs={"rows": 5})}
        labels = {"hero_title": "Homepage headline", "hero_subtitle": "Homepage sub-heading", "about_text": "About the studio"}


class ServiceForm(Styled, forms.ModelForm):
    class Meta:
        model = Service
        fields = ["title", "icon", "short", "description", "includes", "typical_timeline", "image", "order", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4}), "includes": forms.Textarea(attrs={"rows": 4})}
        labels = {"short": "One-line summary", "is_active": "Show on the website"}

    def clean_image(self):
        f = self.cleaned_data.get("image")
        if f and hasattr(f, "content_type"):
            validate_image(f)
        return f

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.slug:
            base = slugify(obj.title)[:45] or "service"
            slug, n = base, 2
            while Service.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            obj.slug = slug
        if commit:
            obj.save()
        return obj


class TestimonialForm(Styled, forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ["name", "city", "project_type", "text", "is_sample", "order", "is_active"]
        widgets = {"text": forms.Textarea(attrs={"rows": 4})}
        labels = {"is_sample": "Mark as “Sample” (untick only for real client reviews)", "is_active": "Show on the website"}


class FAQForm(Styled, forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ["question", "answer", "category", "order", "is_active"]
        widgets = {"answer": forms.Textarea(attrs={"rows": 4})}
        labels = {"is_active": "Show on the website"}


class ProjectForm(Styled, forms.ModelForm):
    class Meta:
        model = PortfolioProject
        fields = ["title", "location", "room_type", "style", "budget_band", "property_type", "area_sqft",
                  "duration_weeks", "year", "summary", "description", "brief", "client_quote", "client_name",
                  "cover", "is_featured", "is_published", "order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5}), "brief": forms.Textarea(attrs={"rows": 3}),
                   "client_quote": forms.Textarea(attrs={"rows": 3})}
        labels = {"area_sqft": "Area (sq ft)", "is_featured": "Feature on the homepage", "is_published": "Published"}

    def clean_cover(self):
        f = self.cleaned_data.get("cover")
        if f and hasattr(f, "content_type"):
            validate_image(f)
        return f


class BeforeAfterForm(Styled, forms.ModelForm):
    class Meta:
        model = BeforeAfter
        fields = ["before", "after", "caption"]

    def clean(self):
        data = super().clean()
        for k in ("before", "after"):
            f = data.get(k)
            if f and hasattr(f, "content_type"):
                try:
                    validate_image(f)
                except forms.ValidationError as e:
                    self.add_error(k, e)
        return data


RoomFormSet = forms.inlineformset_factory(PortfolioProject, ProjectRoom, fields=["name", "description", "order"], extra=1,
                                          can_delete=True, widgets={"description": forms.Textarea(attrs={"rows": 2})})
SwatchFormSet = forms.inlineformset_factory(PortfolioProject, ProjectSwatch, fields=["kind", "name", "hex", "note", "order"],
                                            extra=2, can_delete=True, widgets={"hex": forms.TextInput(attrs={"type": "color"})})


# ------------------------------------------------------------------ 360° house tour (extra feature)
class TourForm(Styled, forms.ModelForm):
    class Meta:
        model = Tour
        fields = ["title", "subtitle", "is_published"]
        labels = {"title": "House / project name", "subtitle": "Short line on the portfolio card"}


class TourRoomForm(Styled, forms.ModelForm):
    """Room details. A new 360° photo is checked (2:1 shape) and resized here; the view stores the result."""

    class Meta:
        model = TourRoom
        fields = ["title", "icon", "panorama", "order", "start_yaw", "start_pitch", "start_hfov"]
        labels = {"title": "Room name", "icon": "Room type (icon)"}
        widgets = {"start_yaw": forms.NumberInput(attrs={"step": "any"}),
                   "start_pitch": forms.NumberInput(attrs={"step": "any"}),
                   "start_hfov": forms.NumberInput(attrs={"step": "any"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed = None
        self.fields["panorama"].widget.attrs["accept"] = "image/jpeg,image/png,image/webp"
        for f in ("start_yaw", "start_pitch", "start_hfov"):
            self.fields[f].help_text = ""

    def clean_panorama(self):
        from .tour360 import process_panorama
        f = self.cleaned_data.get("panorama")
        if f and hasattr(f, "content_type"):   # a new upload
            self.processed = process_panorama(f)
        return f

    def clean(self):
        d = super().clean()
        if d.get("start_pitch") is not None:
            d["start_pitch"] = max(-85.0, min(85.0, d["start_pitch"]))
        if d.get("start_hfov") is not None:
            d["start_hfov"] = max(50.0, min(120.0, d["start_hfov"]))
        return d


class TourHotspotForm(Styled, forms.ModelForm):
    class Meta:
        model = TourHotspot
        fields = ["kind", "title", "tag", "text", "specs", "link_to", "yaw", "pitch"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3}), "specs": forms.Textarea(attrs={"rows": 3}),
                   "yaw": forms.NumberInput(attrs={"step": "any"}), "pitch": forms.NumberInput(attrs={"step": "any"})}
        labels = {"kind": "Type", "title": "Name", "link_to": "Arrow goes to"}

    def __init__(self, *args, room=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.room = room
        qs = room.tour.rooms.exclude(pk=room.pk) if room else self.fields["link_to"].queryset.none()
        self.fields["link_to"].queryset = qs
        self.fields["link_to"].empty_label = "— choose a room —"
        self.fields["yaw"].help_text = self.fields["pitch"].help_text = ""

    def clean(self):
        d = super().clean()
        if d.get("kind") == "link":
            if not d.get("link_to"):
                self.add_error("link_to", "Choose the room this arrow leads to.")
        elif not (d.get("title") or "").strip():
            self.add_error("title", "Give this info dot a name.")
        if d.get("yaw") is not None:
            d["yaw"] = ((d["yaw"] + 180) % 360) - 180
        if d.get("pitch") is not None:
            d["pitch"] = max(-90.0, min(90.0, d["pitch"]))
        return d
