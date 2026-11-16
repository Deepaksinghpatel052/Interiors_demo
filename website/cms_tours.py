"""Studio CMS for the 360° house tour — an extra feature.

While the feature is off, the owner sees what it does and a “Request this feature” button (creates a
ModuleRequest). DEVNIXPLUS switches it on in the Django admin; then the owner manages tours, rooms
(360° photos) and the info dots / room arrows here, placing them by clicking on the photo.
"""
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import ModuleRequest, StudioSettings
from core.modules import EXTRA_FEATURES, extra_on, extra_status
from core.permissions import owner_required
from core.templatetags.studio import wa_link

from . import cms_forms as F
from .models import Tour, TourHotspot, TourRoom

KEY = "tour360"


def tour_required(view):
    """Owner only, and only while the extra feature is switched on (else: back to the request page)."""
    @owner_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not extra_on(KEY):
            messages.info(request, "The 360° house tour is an extra feature. Request it below and we will switch it on.")
            return redirect("cms:tours")
        return view(request, *args, **kwargs)
    return wrapped


@owner_required
def tours(request):
    if not extra_on(KEY):
        feature = EXTRA_FEATURES[KEY]
        pending = ModuleRequest.objects.filter(feature=KEY, status=ModuleRequest.Status.PENDING).first()
        wa = ""
        if settings.DEVNIX_WHATSAPP:
            wa = wa_link(settings.DEVNIX_WHATSAPP, f"Hi {settings.DEVNIX_NAME}, please switch on the “{feature['label']}” "
                                                   f"feature for {StudioSettings.load().name}.")
        return render(request, "cms/tour_request.html", {"feature": feature, "pending": pending, "wa_url": wa,
                                                         "status": extra_status(KEY)})
    items = Tour.objects.annotate(n_rooms=Count("rooms", distinct=True),
                                  n_spots=Count("rooms__hotspots", filter=Q(rooms__hotspots__kind="info")))
    return render(request, "cms/tours.html", {"items": items})


@owner_required
@require_POST
def tour_request(request):
    if extra_on(KEY):
        return redirect("cms:tours")
    note = request.POST.get("note", "").strip()[:1000]
    req = ModuleRequest.objects.filter(feature=KEY, status=ModuleRequest.Status.PENDING).first()
    if req:
        if note:
            req.note = (req.note + "\n" + note).strip() if req.note else note
            req.save(update_fields=["note"])
        messages.info(request, "Your request is already with us — we will let you know as soon as it is switched on.")
    else:
        ModuleRequest.objects.create(feature=KEY, requested_by=request.user, note=note)
        messages.success(request, "Request sent. We will switch the 360° house tour on for you and let you know.")
    return redirect("cms:tours")


# ------------------------------------------------------------------ tours
@tour_required
def tour_edit(request, pk=None):
    obj = get_object_or_404(Tour, pk=pk) if pk else None
    form = F.TourForm(request.POST or None, instance=obj)
    if request.method == "POST":
        if form.is_valid():
            t = form.save()
            messages.success(request, "Tour saved." + ("" if obj else " Now add the first room and its 360° photo."))
            return redirect("cms:tour_edit", pk=t.pk) if obj else redirect("cms:tour_room_new", tour=t.pk)
        messages.error(request, "Please fix the highlighted fields.")
    rooms = obj.rooms.annotate(n_spots=Count("hotspots", filter=Q(hotspots__kind="info")),
                               n_links=Count("hotspots", filter=Q(hotspots__kind="link"))) if obj else []
    return render(request, "cms/tour_form.html", {"form": form, "obj": obj, "rooms": rooms,
                                                  "first_published": _first_published_id()})


@tour_required
@require_POST
def tour_delete(request, pk):
    t = get_object_or_404(Tour, pk=pk)
    title = t.title
    for r in t.rooms.all():
        _delete_files(r)
    t.delete()
    messages.success(request, f"Deleted the tour “{title}”.")
    return redirect("cms:tours")


def _first_published_id():
    t = Tour.objects.filter(is_published=True, rooms__isnull=False).distinct().first()
    return t.pk if t else None


def _delete_files(room):
    for f in (room.panorama, room.preview):
        if f:
            f.delete(save=False)


# ------------------------------------------------------------------ rooms + hotspots
@tour_required
def room_edit(request, tour, pk=None):
    t = get_object_or_404(Tour, pk=tour)
    room = get_object_or_404(TourRoom, pk=pk, tour=t) if pk else None
    action = request.POST.get("action", "room") if request.method == "POST" else ""

    form = F.TourRoomForm(request.POST if action == "room" else None,
                          request.FILES if action == "room" else None, instance=room,
                          initial=None if room else {"order": t.rooms.count(), "start_hfov": 105})
    if room is None:
        form.fields["panorama"].required = True
    if action == "room":
        if form.is_valid():
            r = form.save(commit=False)
            r.tour = t
            old = (room.panorama.name, room.preview.name) if room and form.processed else None
            if form.processed:
                pano, prev = form.processed
                r.panorama.save(pano.name, pano, save=False)
                r.preview.save(prev.name, prev, save=False)
            r.save()
            if old:
                storage = r.panorama.storage
                for name in old:
                    if name:
                        storage.delete(name)
            messages.success(request, "Room saved." + ("" if room else " Now click on the photo to add info dots."))
            return redirect("cms:tour_room", tour=t.pk, pk=r.pk)
        messages.error(request, "Please fix the highlighted fields.")

    spot_form, editing = None, None
    if room:
        editing = room.hotspots.filter(pk=request.POST.get("spot") or request.GET.get("spot") or 0).first()
        spot_form = F.TourHotspotForm(request.POST if action == "spot" else None, instance=editing, room=room,
                                      initial=None if editing else {"kind": "info"}, prefix="spot")
        if action == "spot":
            if spot_form.is_valid():
                h = spot_form.save(commit=False)
                h.room = room
                if not editing:
                    h.order = room.hotspots.count()
                if h.kind == "link":
                    h.title = h.tag = h.text = h.specs = ""
                else:
                    h.link_to = None
                h.save()
                messages.success(request, ("Arrow" if h.kind == "link" else "Info dot") + " saved.")
                return redirect("cms:tour_room", tour=t.pk, pk=room.pk)
            messages.error(request, "Please fix the highlighted fields.")
        elif action == "delete_spot":
            h = get_object_or_404(TourHotspot, pk=request.POST.get("spot"), room=room)
            h.delete()
            messages.success(request, "Removed.")
            return redirect("cms:tour_room", tour=t.pk, pk=room.pk)

    editor = None
    if room and room.panorama:
        editor = {
            "pano": room.panorama.url,
            "start": {"yaw": room.start_yaw, "pitch": room.start_pitch, "hfov": room.start_hfov},
            "editing": editing.pk if editing else None,
            "spots": [{"id": h.pk, "kind": h.kind, "yaw": h.yaw, "pitch": h.pitch,
                       "title": h.title if h.kind == "info" else (h.link_to.title if h.link_to_id else "Room")}
                      for h in room.hotspots.select_related("link_to")],
        }
    return render(request, "cms/tour_room.html", {
        "tour": t, "room": room, "form": form, "spot_form": spot_form, "editing": editing, "editor": editor,
        "hotspots": room.hotspots.select_related("link_to") if room else [],
        "other_rooms": t.rooms.exclude(pk=room.pk) if room else t.rooms.all(),
    })


@tour_required
@require_POST
def room_delete(request, tour, pk):
    room = get_object_or_404(TourRoom, pk=pk, tour_id=tour)
    title = room.title
    with transaction.atomic():
        TourHotspot.objects.filter(link_to=room).delete()
        _delete_files(room)
        room.delete()
    messages.success(request, f"Deleted the room “{title}”.")
    return redirect("cms:tour_edit", pk=tour)
