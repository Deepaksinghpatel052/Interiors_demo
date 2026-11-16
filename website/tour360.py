"""360° house tour helpers: panorama upload processing, the data the portfolio viewer reads, and the sample tour.

The feature is an extra (StudioSettings.module_tour360): off until DEVNIXPLUS switches it on.
"""
import io
import json
import os
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PANO_MB = 30          # 360° camera photos are often 10–25 MB
PANO_WIDTH = 4096         # widest texture most phones can show
PREVIEW_SIZE = (1600, 800)
SEED_DIR = Path(__file__).resolve().parent / "tour_seed"


def _jpeg(img, name, size=None, quality=82):
    img = img.convert("RGB")
    if size:
        img = img.resize(size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    base = os.path.splitext(os.path.basename(name or "panorama"))[0][:60] or "panorama"
    return ContentFile(buf.getvalue(), name=f"{base}.jpg")


def process_panorama(f):
    """Validate an uploaded 360° photo and return (panorama, preview) ContentFiles."""
    if f.size and f.size > MAX_PANO_MB * 1024 * 1024:
        raise ValidationError(f"The photo is too large. The maximum size is {MAX_PANO_MB} MB.")
    ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        raise ValidationError("Please upload a JPG, PNG or WebP photo.")
    try:
        img = ImageOps.exif_transpose(Image.open(f))
        img.load()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("This file is not a valid image.")
    w, h = img.size
    if not 1.9 <= w / h <= 2.1:
        raise ValidationError(f"This is not a 360° photo: it must be twice as wide as it is tall (2:1), "
                              f"but it is {w} × {h}. Export it as “equirectangular” from your 360° camera or app.")
    if w > PANO_WIDTH:
        img = img.resize((PANO_WIDTH, PANO_WIDTH // 2), Image.LANCZOS)
    return _jpeg(img, f.name), _jpeg(img, f.name, size=PREVIEW_SIZE, quality=78)


def make_preview(fileobj, name):
    img = Image.open(fileobj)
    return _jpeg(img, name, size=PREVIEW_SIZE, quality=78)


def published_tour():
    from .models import Tour
    return (Tour.objects.filter(is_published=True, rooms__isnull=False).distinct()
            .prefetch_related("rooms__hotspots").first())


def viewer_data(tour):
    """The JSON the portfolio's tour360.js reads."""
    rooms = list(tour.rooms.all())
    ids = {r.pk for r in rooms}
    data = {"house": tour.title, "rooms": []}
    for r in rooms:
        spots, links = [], []
        for h in r.hotspots.all():
            if h.kind == "link":
                if h.link_to_id in ids and h.link_to_id != r.pk:
                    links.append({"to": f"r{h.link_to_id}", "yaw": h.yaw, "pitch": h.pitch})
            else:
                spots.append({"yaw": h.yaw, "pitch": h.pitch, "tag": h.tag, "title": h.title or "Detail",
                              "text": h.text, "specs": h.spec_list})
        data["rooms"].append({
            "id": f"r{r.pk}", "title": r.title, "icon": r.icon, "pano": r.panorama.url,
            "start": {"yaw": r.start_yaw, "pitch": r.start_pitch, "hfov": r.start_hfov},
            "links": links, "spots": spots,
        })
    return data


def seed_sample_tour(Tour, TourRoom, TourHotspot, storage=None):
    """Create the sample “Aangan Residence” tour from website/tour_seed/. Takes the model classes so a
    data migration can use it with historical models. Does nothing if a tour already exists."""
    if Tour.objects.exists():
        return None
    from django.core.files.storage import default_storage
    storage = storage or default_storage
    seed = json.loads((SEED_DIR / "tour.json").read_text(encoding="utf-8"))
    tour = Tour.objects.create(title=seed["title"], subtitle=seed.get("subtitle", ""), is_sample=True)
    rooms = {}
    for i, r in enumerate(seed["rooms"]):
        src = SEED_DIR / r["image"]
        with open(src, "rb") as fh:
            pano = storage.save(f"tours/{src.name}", ContentFile(fh.read()))
        with open(src, "rb") as fh:
            prev = storage.save(f"tours/previews/{src.name}", make_preview(fh, src.name))
        s = r.get("start", {})
        rooms[r["key"]] = TourRoom.objects.create(
            tour=tour, title=r["title"], icon=r["icon"], panorama=pano, preview=prev, order=i,
            start_yaw=s.get("yaw", 0), start_pitch=s.get("pitch", 0), start_hfov=s.get("hfov", 105))
    for r in seed["rooms"]:
        room = rooms[r["key"]]
        for i, sp in enumerate(r["spots"]):
            TourHotspot.objects.create(room=room, kind="info", yaw=sp["yaw"], pitch=sp["pitch"], tag=sp.get("tag", ""),
                                       title=sp["title"], text=sp.get("text", ""),
                                       specs="\n".join(sp.get("specs", [])), order=i)
        for i, ln in enumerate(r.get("links", [])):
            TourHotspot.objects.create(room=room, kind="link", yaw=ln["yaw"], pitch=ln["pitch"],
                                       link_to=rooms[ln["to"]], order=100 + i)
    return tour


def replace_sample_room(Tour, TourRoom, TourHotspot, key, old_image, storage=None):
    """Swap one room of an already-loaded sample tour for the current seed version (photo, dots, own arrows).
    Used when the sample content changes (e.g. the loft kitchen became a modular kitchen). Arrows from other
    rooms keep pointing at it. Does nothing if that room is not the old sample room."""
    from django.core.files.storage import default_storage
    storage = storage or default_storage
    seed = json.loads((SEED_DIR / "tour.json").read_text(encoding="utf-8"))
    r = next(x for x in seed["rooms"] if x["key"] == key)
    room = TourRoom.objects.filter(tour__is_sample=True, panorama=f"tours/{old_image}").first()
    if room is None:
        return None
    others = {x.title: x for x in TourRoom.objects.filter(tour=room.tour).exclude(pk=room.pk)}
    keys = {x["key"]: x["title"] for x in seed["rooms"]}
    old_files = [room.panorama.name, room.preview.name]
    src = SEED_DIR / r["image"]
    with open(src, "rb") as fh:
        room.panorama = storage.save(f"tours/{src.name}", ContentFile(fh.read()))
    with open(src, "rb") as fh:
        room.preview = storage.save(f"tours/previews/{src.name}", make_preview(fh, src.name))
    s = r.get("start", {})
    room.title, room.icon = r["title"], r["icon"]
    room.start_yaw, room.start_pitch, room.start_hfov = s.get("yaw", 0), s.get("pitch", 0), s.get("hfov", 105)
    room.save()
    TourHotspot.objects.filter(room=room).delete()
    for i, sp in enumerate(r["spots"]):
        TourHotspot.objects.create(room=room, kind="info", yaw=sp["yaw"], pitch=sp["pitch"], tag=sp.get("tag", ""),
                                   title=sp["title"], text=sp.get("text", ""), specs="\n".join(sp.get("specs", [])),
                                   order=i)
    for i, ln in enumerate(r.get("links", [])):
        target = others.get(keys.get(ln["to"]))
        if target:
            TourHotspot.objects.create(room=room, kind="link", yaw=ln["yaw"], pitch=ln["pitch"], link_to=target,
                                       order=100 + i)
    if room.tour.subtitle and seed.get("subtitle"):
        Tour.objects.filter(pk=room.tour_id).update(subtitle=seed["subtitle"])
    for name in old_files:
        if name and storage.exists(name):
            storage.delete(name)
    return room
