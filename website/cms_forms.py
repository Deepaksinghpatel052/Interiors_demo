from django import forms
from django.utils.text import slugify

from core.models import StudioSettings
from core.validators import validate_image
from studio.forms import StyledMixin

from .models import FAQ, BeforeAfter, PortfolioProject, ProjectRoom, ProjectSwatch, Service, Testimonial


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
