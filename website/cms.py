"""Studio-side Website CMS (the “Website + CMS” package): the owner edits the public site without the Django admin."""
from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.images import optimise
from core.models import StudioSettings
from core.permissions import owner_required
from core.validators import validate_image

from . import cms_forms as F
from .models import FAQ, BeforeAfter, PortfolioProject, ProjectImage, Service, Testimonial

MAX_BATCH = 12

# kind -> (model, form, plural label, singular label, icon, columns shown in the list)
SIMPLE = {
    "services": (Service, F.ServiceForm, "Services", "service", "briefcase", ["short"]),
    "testimonials": (Testimonial, F.TestimonialForm, "Testimonials", "testimonial", "chat-quote", ["city", "project_type"]),
    "faqs": (FAQ, F.FAQForm, "FAQs", "FAQ", "question-circle", ["category"]),
}


def _simple(kind):
    if kind not in SIMPLE:
        raise Http404
    return SIMPLE[kind]


def _title(obj):
    return getattr(obj, "title", None) or getattr(obj, "question", None) or getattr(obj, "name", "")


def _style_formset(fs):
    for f in fs.forms:
        for name, field in f.fields.items():
            w = field.widget
            if field.label and not isinstance(w, forms.HiddenInput):
                w.attrs.setdefault("aria-label", str(field.label))
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")
            elif isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select form-select-sm")
            elif name == "hex":
                w.attrs.setdefault("class", "form-control form-control-color")
            else:
                w.attrs.setdefault("class", "form-control form-control-sm")
    return fs


def _optimise_field(obj, field):
    f = getattr(obj, field)
    if f and hasattr(f, "file") and not getattr(f, "_committed", True):
        setattr(obj, field, optimise(f.file, f.name))


# ------------------------------------------------------------------ hub + homepage
@owner_required
def index(request):
    s = StudioSettings.load()
    form = F.HomepageForm(request.POST or None, instance=s)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Homepage text saved — it is live on the website.")
            return redirect("cms:index")
        messages.error(request, "Please fix the highlighted fields.")
    sections = [
        ("projects", "Portfolio projects", "images", PortfolioProject.objects.count(), "Photos, before/after, mood boards"),
        ("services", "Services", "briefcase", Service.objects.count(), "What you offer and what is included"),
        ("testimonials", "Testimonials", "chat-quote", Testimonial.objects.count(), "Client words (mark samples)"),
        ("faqs", "FAQs", "question-circle", FAQ.objects.count(), "Also used by the AI assistant"),
    ]
    return render(request, "cms/index.html", {"form": form, "sections": sections})


# ------------------------------------------------------------------ services / testimonials / FAQs
@owner_required
def item_list(request, kind):
    model, _, plural, singular, icon, cols = _simple(kind)
    items = [{"obj": o, "title": _title(o), "meta": " · ".join(str(getattr(o, c)) for c in cols if getattr(o, c))}
             for o in model.objects.all()]
    return render(request, "cms/list.html", {"kind": kind, "plural": plural, "singular": singular, "icon": icon, "items": items})


@owner_required
def item_edit(request, kind, pk=None):
    model, form_cls, plural, singular, icon, _ = _simple(kind)
    obj = get_object_or_404(model, pk=pk) if pk else None
    form = form_cls(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST":
        if form.is_valid():
            item = form.save(commit=False)
            if hasattr(item, "image"):
                _optimise_field(item, "image")
            item.save()
            messages.success(request, f"{singular[:1].upper() + singular[1:]} saved.")
            return redirect("cms:list", kind=kind)
        messages.error(request, "Please fix the highlighted fields.")
    return render(request, "cms/form.html", {"form": form, "kind": kind, "plural": plural, "singular": singular,
                                             "obj": obj, "title": _title(obj) if obj else f"New {singular}"})


@owner_required
@require_POST
def item_delete(request, kind, pk):
    model, _, _, singular, _, _ = _simple(kind)
    obj = get_object_or_404(model, pk=pk)
    title = _title(obj)
    obj.delete()
    messages.success(request, f"Deleted “{title}”.")
    return redirect("cms:list", kind=kind)


# ------------------------------------------------------------------ portfolio
@owner_required
def projects(request):
    items = PortfolioProject.objects.prefetch_related("images")
    return render(request, "cms/projects.html", {"items": items})


@owner_required
def project_edit(request, pk=None):
    obj = get_object_or_404(PortfolioProject, pk=pk) if pk else None
    form = F.ProjectForm(request.POST or None, request.FILES or None, instance=obj)
    if obj is None:
        form.fields["cover"].required = True
    if request.method == "POST":
        if form.is_valid():
            p = form.save(commit=False)
            _optimise_field(p, "cover")
            p.save()
            messages.success(request, "Project saved." + ("" if obj else " Now add gallery photos."))
            return redirect("cms:project_media", pk=p.pk) if obj is None else redirect("cms:project_edit", pk=p.pk)
        messages.error(request, "Please fix the highlighted fields.")
    return render(request, "cms/project_form.html", {"form": form, "obj": obj, "tab": "details"})


@owner_required
def project_media(request, pk):
    p = get_object_or_404(PortfolioProject, pk=pk)
    ba_form = F.BeforeAfterForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "upload":
            files = request.FILES.getlist("images")[:MAX_BATCH]
            added, errors = 0, []
            start = (p.images.order_by("-order").values_list("order", flat=True).first() or 0) + 1
            for i, f in enumerate(files):
                try:
                    validate_image(f)
                except forms.ValidationError as e:
                    errors.append(f"{f.name}: {e.messages[0]}")
                    continue
                ProjectImage.objects.create(project=p, image=optimise(f, f.name), order=start + i,
                                            room=p.get_room_type_display())
                added += 1
            if added:
                messages.success(request, f"{added} photo{'s' if added != 1 else ''} added to the gallery.")
            for e in errors[:3]:
                messages.error(request, e)
            if not files:
                messages.error(request, "Choose one or more photos first.")
        elif action == "save":
            with transaction.atomic():
                for img in p.images.all():
                    if request.POST.get(f"delete-{img.pk}"):
                        img.image.delete(save=False)
                        img.delete()
                        continue
                    img.caption = request.POST.get(f"caption-{img.pk}", img.caption)[:160]
                    img.in_mood_board = bool(request.POST.get(f"mood-{img.pk}"))
                    try:
                        img.order = max(0, int(request.POST.get(f"order-{img.pk}", img.order)))
                    except ValueError:
                        pass
                    img.save()
            messages.success(request, "Gallery saved.")
        elif action == "cover":
            img = get_object_or_404(ProjectImage, pk=request.POST.get("image"), project=p)
            img.image.open("rb")
            p.cover.save(img.image.name.rsplit("/", 1)[-1], optimise(img.image.file, img.image.name), save=True)
            img.image.close()
            messages.success(request, "Cover photo updated.")
        elif action == "before_after":
            ba_form = F.BeforeAfterForm(request.POST, request.FILES)
            if ba_form.is_valid():
                ba = ba_form.save(commit=False)
                ba.project = p
                _optimise_field(ba, "before")
                _optimise_field(ba, "after")
                ba.order = p.before_afters.count()
                ba.save()
                messages.success(request, "Before/after pair added.")
            else:
                messages.error(request, "Please choose both a before and an after photo.")
                return render(request, "cms/project_media.html", {"obj": p, "ba_form": ba_form, "tab": "media"})
        elif action == "delete_ba":
            get_object_or_404(BeforeAfter, pk=request.POST.get("pair"), project=p).delete()
            messages.success(request, "Before/after pair removed.")
        return redirect("cms:project_media", pk=p.pk)
    return render(request, "cms/project_media.html", {"obj": p, "ba_form": ba_form, "tab": "media"})


@owner_required
def project_moodboard(request, pk):
    p = get_object_or_404(PortfolioProject, pk=pk)
    rooms = _style_formset(F.RoomFormSet(request.POST or None, instance=p, prefix="rooms"))
    swatches = _style_formset(F.SwatchFormSet(request.POST or None, instance=p, prefix="sw"))
    if request.method == "POST":
        if rooms.is_valid() and swatches.is_valid():
            with transaction.atomic():
                rooms.save()
                swatches.save()
            messages.success(request, "Mood board saved.")
            return redirect("cms:project_moodboard", pk=p.pk)
        messages.error(request, "Please fix the highlighted rows.")
    return render(request, "cms/project_moodboard.html", {"obj": p, "rooms": rooms, "swatches": swatches, "tab": "mood"})


@owner_required
@require_POST
def project_delete(request, pk):
    p = get_object_or_404(PortfolioProject, pk=pk)
    title = p.title
    p.delete()
    messages.success(request, f"Deleted “{title}” from the portfolio.")
    return redirect("cms:projects")
