from datetime import datetime, timezone as dt_timezone
from urllib.parse import urlencode

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from core.models import StudioSettings
from crm.models import Lead, LeadActivity
from website.models import Style

from .forms import BookingForm
from .models import Booking
from .slots import bookable_days, slots_for_date

SESSION_KEY = "my_bookings"


def _remember(request, ref):
    refs = request.session.get(SESSION_KEY, [])
    request.session[SESSION_KEY] = (refs + [ref])[-10:]


def _owned_booking(request, ref):
    if ref not in request.session.get(SESSION_KEY, []):
        raise Http404
    return get_object_or_404(Booking, reference=ref)


def _find_or_create_lead(data, style):
    """Reuse an open lead with the same mobile (e.g. from the estimator) instead of duplicating."""
    lead = (Lead.objects.filter(mobile=data["mobile"])
            .exclude(stage__in=[Lead.Stage.WON, Lead.Stage.LOST]).order_by("-created_at").first())
    if lead is None:
        lead = Lead(mobile=data["mobile"], source=Lead.Source.WEBSITE)
    lead.name = data["name"]
    lead.email = data["email"] or lead.email
    lead.property_type = data["property_type"] or lead.property_type
    lead.budget_band = data["budget_band"] or lead.budget_band
    if style:
        lead.style_preference = style
    if data["notes"]:
        lead.message = (lead.message + "\n\n" if lead.message else "") + data["notes"]
    if lead.stage in (Lead.Stage.NEW, Lead.Stage.CONTACTED, ""):
        lead.stage = Lead.Stage.CONSULTATION
    lead.save()
    return lead


def book(request):
    quiz_style = request.session.get("quiz_style", "")
    style = request.GET.get("style") or quiz_style
    style = style if style in Style.values else ""
    initial = {"style": style}
    if request.GET.get("project"):
        initial["notes"] = f"I liked your project “{request.GET['project'][:120]}” and want something similar."
    if request.GET.get("mode") in Booking.Mode.values:
        initial["mode"] = request.GET["mode"]

    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            style = d["style"] if d["style"] in Style.values else ""
            try:
                with transaction.atomic():
                    lead = _find_or_create_lead(d, style)
                    booking = Booking.objects.create(
                        lead=lead, mode=d["mode"], date=d["date"], start_time=d["time"],
                        kind=Booking.Kind.SITE_VISIT if d["mode"] == Booking.Mode.SITE else Booking.Kind.CONSULTATION,
                        name=d["name"], mobile=d["mobile"], email=d["email"],
                        site_address=d["site_address"], notes=d["notes"])
                    LeadActivity.objects.create(
                        lead=lead, text=f"Booked {booking.get_mode_display().lower()} for "
                                        f"{booking.date:%d-%m-%Y} at {booking.start_time:%I:%M %p} ({booking.reference})")
                    if quiz_style:
                        LeadActivity.objects.create(lead=lead, text=f"Style quiz result: {Style(quiz_style).label}")
            except IntegrityError:
                messages.error(request, "Sorry, someone just booked that slot. Please pick another time.")
            else:
                _remember(request, booking.reference)
                return redirect("bookings:confirmed", ref=booking.reference)
        else:
            messages.error(request, "Please check the highlighted details.")
    else:
        form = BookingForm(initial=initial)

    return render(request, "bookings/book.html", {
        "form": form,
        "days": bookable_days(),
        "style_label": Style(style).label if style else "",
        "modes": [
            ("studio", "building", "At our studio", "See materials and samples in person"),
            ("online", "camera-video", "Online", "Video call from wherever you are"),
            ("site_visit", "geo-alt", "Site visit", "We come to your home or office"),
        ],
    })


@require_GET
def api_slots(request):
    try:
        day = datetime.strptime(request.GET.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date"}, status=400)
    return JsonResponse({"date": day.isoformat(), "slots": slots_for_date(day)})


def _calendar_texts(booking):
    s = StudioSettings.load()
    title = f"{booking.get_kind_display()} with {s.name}"
    location = {
        Booking.Mode.STUDIO: s.address,
        Booking.Mode.SITE: booking.site_address,
        Booking.Mode.ONLINE: "Online — the video link will be shared on WhatsApp",
    }[booking.mode]
    details = f"Booking reference {booking.reference}. Questions? Call {s.phone}."
    return title, location, details


def confirmed(request, ref):
    booking = _owned_booking(request, ref)
    title, location, details = _calendar_texts(booking)
    fmt = "%Y%m%dT%H%M%SZ"
    gcal = "https://calendar.google.com/calendar/render?" + urlencode({
        "action": "TEMPLATE", "text": title, "details": details, "location": location,
        "dates": f"{booking.start.astimezone(dt_timezone.utc):{fmt}}/{booking.end.astimezone(dt_timezone.utc):{fmt}}",
    })
    wa_text = (f"Hi, I have booked a {booking.get_kind_display().lower()} ({booking.get_mode_display().lower()}) "
               f"on {booking.date:%d-%m-%Y} at {booking.start_time:%I:%M %p}. Reference {booking.reference}. — {booking.name}")
    return render(request, "bookings/confirmed.html", {"booking": booking, "gcal_url": gcal, "wa_text": wa_text,
                                                       "location": location})


def _ics_escape(text):
    return (text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n"))


def ics(request, ref):
    booking = _owned_booking(request, ref)
    title, location, details = _calendar_texts(booking)
    s = StudioSettings.load()
    fmt = "%Y%m%dT%H%M%SZ"
    utc = dt_timezone.utc
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Studio Demo//Bookings//EN", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH", "BEGIN:VEVENT",
        f"UID:{booking.reference}@{request.get_host().split(':')[0]}",
        f"DTSTAMP:{booking.created_at.astimezone(utc):{fmt}}",
        f"DTSTART:{booking.start.astimezone(utc):{fmt}}",
        f"DTEND:{booking.end.astimezone(utc):{fmt}}",
        f"SUMMARY:{_ics_escape(title)}",
        f"LOCATION:{_ics_escape(location)}",
        f"DESCRIPTION:{_ics_escape(details)}",
        f"ORGANIZER;CN={_ics_escape(s.name)}:mailto:{s.email}",
        "BEGIN:VALARM", "TRIGGER:-PT1H", "ACTION:DISPLAY", f"DESCRIPTION:{_ics_escape(title)}", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR",
    ]
    resp = HttpResponse("\r\n".join(lines) + "\r\n", content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{booking.reference}.ics"'
    return resp
