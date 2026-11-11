import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from core.models import StudioSettings
from core.templatetags.studio import format_inr

from crm.models import Lead, LeadActivity

from . import estimator, quiz
from .forms import EnquiryForm, EstimateLeadForm
from .models import (FAQ, BudgetBand, PhotoCredit, PortfolioProject, RoomType, Service, Style,
                     Testimonial)

PROCESS_STEPS = [
    ("chat-heart", "Consultation", "A relaxed conversation about how you live, your budget and your timeline."),
    ("rulers", "Site visit", "We measure every wall, check services and photograph the space."),
    ("palette", "Design & 3D", "Layouts, mood boards and 3D views you approve online, version by version."),
    ("hammer", "Execution", "Our supervised team builds it — with weekly photo updates in your portal."),
    ("key", "Handover", "Deep cleaning, styling and a walkthrough. Then your warranty begins."),
]


def _published():
    return PortfolioProject.objects.filter(is_published=True)


WHY_US = [
    ("receipt", "Itemised GST quotations", "Every material, quantity and rate listed. What you approve is what you pay."),
    ("phone", "Your project, online", "Designs, approvals, payments and site photos in your private client portal."),
    ("calendar2-check", "Milestone-based timeline", "Clear dates for design, ordering, execution and handover — tracked weekly."),
    ("people", "In-house supervised team", "Our own site supervisors check every stage, so quality never depends on luck."),
    ("badge-3d", "See it before it's built", "Mood boards, material samples and 3D views before a single panel is cut."),
    ("shield-check", "Written warranty", "Warranty on workmanship and modular furniture, documented at handover."),
]


def demo_home(request):
    """The studio home lives at /demo/ only while the product landing page owns / (LANDING_PAGE=True)."""
    from django.conf import settings
    if not settings.LANDING_PAGE:
        return redirect("/")
    return home(request)


def home(request):
    from bookings.slots import bookable_days, slots_for_date

    published = list(_published().prefetch_related("images", "before_afters"))
    featured = [p for p in published if p.is_featured][:6]
    if len(featured) < 6:  # keep the grid full: top up with other published projects
        featured += [p for p in published if p not in featured][:6 - len(featured)]

    # Explore by room: one tile per room type that has projects
    rooms = []
    for value, label in RoomType.choices:
        items = [p for p in published if p.room_type == value]
        if items:
            rooms.append({"value": value, "label": label, "count": len(items), "cover": items[-1].cover})
    # Spotlight: a featured project with a before/after pair, different from the hero
    spotlight = next((p for p in featured[1:] if p.before_afters.all()), None)
    # Photo mosaic from gallery images across projects
    moments = []
    for p in published:
        for img in p.images.all()[:2]:
            moments.append((p, img))
    # Next free consultation slot (real availability)
    next_slot = None
    for day in bookable_days(count=1):
        free = [s for s in slots_for_date(day["date"]) if s["available"]]
        if free:
            next_slot = {"date": day["date"], "label": free[0]["label"]}

    return render(request, "website/home.html", {
        "hero": featured[0] if featured else None,
        "featured": featured,
        "rooms": rooms,
        "spotlight": spotlight,
        "moments": moments[:10],
        "next_slot": next_slot,
        "why_us": WHY_US,
        "services": Service.objects.filter(is_active=True)[:6],
        "testimonials": Testimonial.objects.filter(is_active=True)[:3],
        "faqs": FAQ.objects.filter(is_active=True)[:5],
        "steps": PROCESS_STEPS,
        "project_count": len(published),
        "style_count": len({p.style for p in published}),
        "city_count": len({p.location.split(",")[-1].strip() for p in published}),
    })


def portfolio(request):
    room, style, budget = (request.GET.get(k, "") for k in ("room", "style", "budget"))
    room = room if room in RoomType.values else ""
    style = style if style in Style.values else ""
    budget = budget if budget in BudgetBand.values else ""
    # All projects are rendered; non-matching ones start hidden so links are shareable
    # and jQuery can filter instantly without reloading.
    projects = list(_published())
    for i, p in enumerate(projects):
        p.tall = i % 3 == 1
        p.visible = ((not room or p.room_type == room) and (not style or p.style == style)
                     and (not budget or p.budget_band == budget))
    def counted(choices, attr):
        return [(v, l, sum(getattr(p, attr) == v for p in projects)) for v, l in choices]
    return render(request, "website/portfolio.html", {
        "projects": projects,
        "visible_count": sum(p.visible for p in projects),
        "collage": [p for p in projects if p.is_featured][:3] or projects[:3],
        "rooms": counted(RoomType.choices, "room_type"), "styles": counted(Style.choices, "style"),
        "budgets": counted(BudgetBand.choices, "budget_band"),
        "current": {"room": room, "style": style, "budget": budget},
    })


def project_detail(request, slug):
    project = get_object_or_404(
        _published().prefetch_related("images", "before_afters", "rooms", "swatches", "timeline"), slug=slug)
    related = _published().filter(style=project.style).exclude(pk=project.pk)[:3]
    if related.count() < 3:
        related = _published().exclude(pk=project.pk)[:3]
    return render(request, "website/project_detail.html", {"project": project, "related": related})


def services(request):
    return render(request, "website/services.html", {
        "services": Service.objects.filter(is_active=True), "steps": PROCESS_STEPS})


def about(request):
    return render(request, "website/about.html", {
        "steps": PROCESS_STEPS,
        "why_us": WHY_US,
        "collage": list(_published().order_by("-is_featured", "order")[:4]),
        "project_count": _published().count(),
        "testimonials": Testimonial.objects.filter(is_active=True)[:2],
    })


def faq(request):
    faqs = FAQ.objects.filter(is_active=True)
    grouped = {}
    for f in faqs:
        grouped.setdefault(f.category, []).append(f)
    return render(request, "website/faq.html", {"grouped": grouped})


def privacy(request):
    return render(request, "website/privacy.html")


def photo_credits(request):
    return render(request, "website/credits.html", {"credits": PhotoCredit.objects.all()})


def _handle_enquiry(request, template, intent):
    initial = {}
    style = request.GET.get("style")
    if style in Style.values:
        initial["style_preference"] = style
    if request.GET.get("project"):
        initial["message"] = f"I liked your project “{request.GET['project'][:120]}” and want something similar."

    if request.method == "POST":
        form = EnquiryForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.source = Lead.Source.WEBSITE
            lead.city = ""
            lead.save()
            LeadActivity.objects.create(lead=lead, text=f"{intent} submitted on the website")
            request.session["last_lead_id"] = lead.pk
            return redirect(reverse("website:thanks"))
        messages.error(request, "Please check the highlighted fields.")
    else:
        form = EnquiryForm(initial=initial)
    return render(request, template, {"form": form})


def contact(request):
    return _handle_enquiry(request, "website/contact.html", "Enquiry")


def thanks(request):
    lead = None
    if request.session.get("last_lead_id"):
        lead = Lead.objects.filter(pk=request.session["last_lead_id"]).first()
    return render(request, "website/thanks.html", {"lead": lead})


# ---------------------------------------------------------------- showcase tools
def moodboard(request, slug):
    project = get_object_or_404(_published().prefetch_related("images", "swatches", "rooms"), slug=slug)
    others = _published().exclude(pk=project.pk)[:8]
    return render(request, "website/moodboard.html", {
        "project": project, "images": project.images.filter(in_mood_board=True)[:6], "others": others})


def style_quiz(request):
    return render(request, "website/quiz.html", {"questions": quiz.build_questions()})


@require_POST
def style_quiz_result(request):
    answers = [request.POST.get(q["key"], "") for q in quiz.QUESTIONS]
    style = quiz.score(answers)
    if not style:
        messages.error(request, "Please answer the questions to see your style.")
        return redirect("website:quiz")
    request.session["quiz_style"] = style
    projects = _published().filter(style=style)[:3]
    return render(request, "website/quiz_result.html", {
        "style": style, "style_label": Style(style).label, "description": quiz.DESCRIPTIONS[style],
        "palette": quiz.PALETTES[style], "materials": quiz.MATERIALS[style], "projects": projects,
        "share": sum(1 for a in answers if a == style),
    })


# ---------------------------------------------------------------- cost estimator
def _estimate_from(data):
    return estimator.calculate(
        data.get("property_type"), data.getlist("rooms") if hasattr(data, "getlist") else data.get("rooms", []),
        data.get("finish"), data.get("area"), StudioSettings.load())


def estimate(request):
    result, error = None, None
    form = EstimateLeadForm()
    if request.method == "POST":
        try:
            result = _estimate_from(request.POST)
        except ValueError as e:
            error = str(e)
        form = EstimateLeadForm(request.POST)
        if result and form.is_valid():
            d = form.cleaned_data
            lead = Lead.objects.create(
                name=d["name"], mobile=d["mobile"], email=d["email"], source=Lead.Source.ESTIMATOR,
                property_type=result["property_type"],
                style_preference=request.session.get("quiz_style", ""),
                estimate=result,
                message=f"Estimator: {result['property_label']}, {result['area']} sq ft, {result['finish_label']} finish — "
                        f"{format_inr(result['low'])} to {format_inr(result['high'])} (indicative).")
            LeadActivity.objects.create(lead=lead, text="Requested an exact quote from the cost estimator")
            request.session["last_lead_id"] = lead.pk
            return redirect("website:thanks")
        if not error:
            messages.error(request, "Please check your name and mobile number.")
    return render(request, "website/estimate.html", {
        "form": form, "result": result, "error": error,
        "property_types": estimator.PROPERTY_TYPES, "rooms": estimator.ROOMS,
        "finishes": estimator.FINISHES,
        "default_rooms_json": json.dumps(estimator.DEFAULT_ROOMS),
        "room_areas_json": json.dumps({k: v[1] for k, v in estimator.ROOMS.items()}),
        "posted_rooms": request.POST.getlist("rooms") if request.method == "POST" else [],
    })


@require_GET
def api_estimate(request):
    try:
        result = _estimate_from(request.GET)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse(result)


# ===================================================================== /why (sales page, demo mode only)
PROBLEMS = [
    ("whatsapp", "Enquiries get lost in WhatsApp",
     "Messages from Instagram, calls and referrals are spread across phones. Some are never answered.",
     "Website + Studio ERP", "Every enquiry lands on one leads board with its source, stage and next follow-up date.",
     ("studio:leads", "Leads board")),
    ("images", "Designs shared as scattered images",
     "Clients scroll back through chats to find the latest version, and approvals are “seen” ticks.",
     "Client portal", "Each design version lives in the portal with comments and a clear Approve / Request changes.",
     ("portal:designs", "Client portal")),
    ("file-earmark-spreadsheet", "Quotations made by hand",
     "Copying rates into Excel takes hours, GST is error-prone, and every quote looks different.",
     "Quotations & invoices", "Room-wise items from your catalogue, GST split and a branded PDF in minutes.",
     ("finance:quotations", "Quotation builder")),
    ("cash-coin", "Chasing payments",
     "Nobody is sure which milestone is due or who has paid. Reminders feel awkward.",
     "Invoices + Automation", "Milestone invoices, balances, and polite reminders prepared automatically.",
     ("automations:index", "Automations")),
    ("bar-chart", "No view of the business",
     "How many leads came this month? Which projects are late? The answers live in your head.",
     "Owner dashboard + AI", "Leads, conversion, projects and money in one view — and an assistant that knows your studio.",
     ("studio:dashboard", "Dashboard")),
]


def why(request):
    from django.conf import settings
    from django.http import Http404

    from .models import Package
    if not settings.DEMO_MODE:
        raise Http404
    packages = list(Package.objects.filter(is_active=True))
    offer = [{"key": p.key, "name": p.name, "tagline": p.tagline, "includes": p.include_list,
              "price": p.price_text, "bundle": p.is_bundle} for p in packages]
    problems = [{"icon": i, "title": t, "pain": pain, "module": m, "fix": fix, "url": reverse(u), "label": label,
                 "role": "client" if u.startswith("portal:") else "owner"}
                for i, t, pain, m, fix, (u, label) in PROBLEMS]
    return render(request, "website/why.html", {
        "problems": problems, "packages": packages, "offer": offer,
        "easy_payment": [line for line in StudioSettings.load().easy_payment_text.splitlines() if line.strip()],
    })
