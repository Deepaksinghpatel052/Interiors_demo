"""Real demo photography.

`core/demo_photos.json` lists curated CC0 interior photos (Rawpixel / StockSnap via Openverse) with credits.
`fetch()` downloads them once into MEDIA_ROOT/demo_photos (validated + re-encoded with Pillow).
`apply()` puts them on portfolio projects, services, design proposals and site updates.
If a photo is missing (offline setup), the generated illustrations are kept as a fallback.
"""
import io
import json
import time
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image

from core.demo_more_designs import MORE_PHOTOS

MANIFEST = Path(__file__).with_name("demo_photos.json")
MAX_BYTES = 15 * 1024 * 1024
MAX_WIDTH = 1600

# ---------------------------------------------------------------- which photo goes where
PROJECT_PHOTOS = {
    "The Courtyard Home": {"cover": "living-47", "gallery": ["living-13", "dining-02", "kitchen-33", "bedroom-10", "bathroom-00"], "before": "empty-07"},
    "Teal & Teak 2BHK": {"cover": "living-31", "gallery": ["living-15", "living-42", "dining-00"], "before": "empty-04"},
    "Ivory Calm Bedroom": {"cover": "bedroom-01", "gallery": ["bedroom-13", "bedroom-07", "bedroom-16", "bedroom2-10"], "before": "empty-09"},
    "Emerald Island Kitchen": {"cover": "kitchen-30", "gallery": ["kitchen-19", "kitchen-25", "kitchen-23", "dining-09"], "before": "construction-00"},
    "Studio North Office": {"cover": "office-07", "gallery": ["office-14", "office-19", "office-10"], "before": "empty-01"},
    "Saffron Saree Boutique": {"cover": "retail-02", "gallery": ["retail-06", "retail-08", "retail-13", "retail-00"], "before": "construction-10"},
    "Monochrome 3BHK": {"cover": "living-45", "gallery": ["living-43", "kitchen-26", "bedroom-09", "dining-17", "bathroom-09"], "before": "empty-00"},
    "Heritage Haveli Bedroom": {"cover": "bedroom-03", "gallery": ["bedroom-15", "bedroom-21", "bedroom2-07"], "before": "empty-17"},
    "Sage Parallel Kitchen": {"cover": "kitchen-21", "gallery": ["kitchen-20", "kitchen-24", "kitchen-31"], "before": "empty-09"},
    "The Gold Room Lounge": {"cover": "living-40", "gallery": ["living-32", "dining-12", "living-26", "living2-08"], "before": "construction-01"},
    "Skyline Co-working Hub": {"cover": "office-36", "gallery": ["office-32", "office-34", "office-06", "cowork-08"], "before": "empty-01"},
    "Founders’ Cabin, Arera Hills": {"cover": "office-01", "gallery": ["apartment-23", "apartment-26", "apartment-24"]},
    "Noor Jewellers Showroom": {"cover": "showroom-04", "gallery": ["showroom-13", "retail-01", "cafe-18"]},
    "Brew & Bloom Café": {"cover": "cafe-07", "gallery": ["cafe-06", "cafe-01", "cafe-12", "cafe-17", "cafe-13"]},
    "Urban Nest 1BHK": {"cover": "apartment-14", "gallery": ["apartment-19", "apartment-22", "apartment-31", "bathroom-14"], "before": "construction-04"},
    "Blue Hour Living Room": {"cover": "apartment-10", "gallery": ["apartment-15", "living2-12", "living2-06"], "before": "apartment-05"},
    "Royal Suite Bedroom": {"cover": "bedroom2-14", "gallery": ["bedroom2-16", "bedroom2-19", "bathroom-01", "bedroom2-15"]},
    "Pearl White Island Kitchen": {"cover": "kitchen-32", "gallery": ["kitchen-34", "apartment-16", "kitchen-18"], "before": "construction-05"},
    "Riverside Family Home": {"cover": "apartment-03", "gallery": ["apartment-00", "apartment-02", "apartment-20", "bathroom-04", "apartment-17"]},
}
PROJECT_PHOTOS.update(MORE_PHOTOS)

SERVICE_PHOTOS = {
    "residential-interiors": "living-00", "modular-kitchens": "kitchen-17", "wardrobes-storage": "bedroom-21",
    "office-commercial": "office-22", "renovation": "construction-06", "turnkey-execution": "living-38",
    "design-consultation": "dining-03",
}
# Design proposals by project style/room, used in order for each proposal's images
PROPOSAL_POOL = {
    "office": ["office-04", "office-12", "office-15", "office-16", "office-31", "office-33"],
    "default": ["living-00", "dining-04", "bedroom-07", "living-26", "dining-09", "bedroom-13",
                "living-11", "bedroom-04", "living-14", "kitchen-27", "living-19", "kitchen-29",
                "living-02", "dining-11", "living-12", "kitchen-22"],
}
SITE_POOL = ["construction-03", "construction-04", "construction-05", "construction-06",
             "construction-07", "construction-08", "construction-10", "construction-00"]


# photo key prefix -> (room used by the style quiz, caption label)
ROOM_OF = {
    "living": ("living", "Living room"), "living2": ("living", "Living room"), "apartment": ("living", "Home interior"),
    "bedroom": ("bedroom", "Bedroom"), "bedroom2": ("bedroom", "Bedroom"), "kitchen": ("kitchen", "Kitchen"),
    "dining": ("dining", "Dining"), "bathroom": ("bathroom", "Bathroom"), "office": ("office", "Workspace"),
    "cowork": ("office", "Workspace"), "retail": ("retail", "Store"), "showroom": ("retail", "Showroom"),
    "cafe": ("retail", "Café"),
}


def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["photos"]


def photo_dir():
    return Path(settings.MEDIA_ROOT) / "demo_photos"


def local_path(key):
    return photo_dir() / f"{key}.jpg"


def available(key):
    return local_path(key).exists()


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "StudioDemoSetup/1.0 (demo photo fetch)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("file too large")
    return data


def _clean_jpeg(data, max_width=MAX_WIDTH):
    """Validate untrusted bytes with Pillow and re-encode (drops metadata, fixes size/format)."""
    Image.open(io.BytesIO(data)).verify()
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    if im.width > max_width:
        im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return out.getvalue()


def fetch(stdout=None, force=False):
    """Download all manifest photos that are not yet on disk. Returns (downloaded, failed)."""
    photo_dir().mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []
    for p in manifest():
        dest = local_path(p["key"])
        if dest.exists() and not force:
            continue
        try:
            dest.write_bytes(_clean_jpeg(_download(p["url"])))
            ok += 1
            if stdout:
                stdout.write(f"  ok {p['key']}")
            time.sleep(0.3)
        except Exception as e:  # network or invalid image: keep going, fallback stays in place
            failed.append(p["key"])
            if stdout:
                stdout.write(f"  FAILED {p['key']}: {e}")
    return ok, failed


def as_file(key, max_width=None):
    data = local_path(key).read_bytes()
    if max_width:
        im = Image.open(io.BytesIO(data))
        if im.width > max_width:
            data = _clean_jpeg(data, max_width)
    return ContentFile(data)


def _set(field, key, name, max_width=None):
    """Replace an ImageField's file with a downloaded photo. Returns True if replaced."""
    if not available(key):
        return False
    if field:
        field.delete(save=False)
    field.save(f"{name}.jpg", as_file(key, max_width), save=False)
    return True


def apply_project(project, used, stdout=None):
    """Put the real photos listed in PROJECT_PHOTOS on one portfolio project. Adds used keys to `used`."""
    from website.models import BeforeAfter, ProjectImage

    spec = PROJECT_PHOTOS.get(project.title)
    if not spec or not available(spec["cover"]):
        return False
    _set(project.cover, spec["cover"], f"{project.slug}-cover")
    project.save()
    used.add(spec["cover"])
    gallery = [k for k in spec["gallery"] if available(k)]
    if gallery:
        for img in project.images.all():
            img.image.delete(save=False)
        project.images.all().delete()
        for i, key in enumerate(gallery):
            room, label = ROOM_OF.get(key.split("-")[0], ("living", "Interior"))
            im = ProjectImage(project=project, room=room, order=i, caption=f"{label} — {project.title}")
            _set(im.image, key, f"{project.slug}-{i}", 1200)
            im.save()
            used.add(key)
    if not spec.get("before"):
        for ba in project.before_afters.all():
            ba.before.delete(save=False)
            ba.after.delete(save=False)
        project.before_afters.all().delete()
    elif available(spec["before"]):
        for ba in project.before_afters.all():
            ba.before.delete(save=False)
            ba.after.delete(save=False)
        project.before_afters.all().delete()
        ba = BeforeAfter(project=project, caption="Before work started, and the finished space at handover.")
        _set(ba.before, spec["before"], f"{project.slug}-before", 1400)
        _set(ba.after, spec["cover"], f"{project.slug}-after", 1400)
        ba.save()
        used.add(spec["before"])
    if stdout:
        stdout.write(f"  · {project.title}")
    return True


def add_credits(keys):
    """Add a photo-credits row for each photo key that is not credited yet."""
    from website.models import PhotoCredit

    have = set(PhotoCredit.objects.values_list("url", flat=True))
    added = 0
    for p in manifest():
        url = p["landing"] or p["url"]
        if p["key"] in keys and url not in have:
            PhotoCredit.objects.create(description=(p["title"] or p["category"].title())[:200],
                                       author=p["creator"][:120] or "Unknown",
                                       source=f"{p['source'].title()} · {p['license'].upper()}", url=url)
            have.add(url)
            added += 1
    return added


def apply(stdout=None):
    """Put real photos on existing demo records (keeps all leads, bookings and projects)."""
    from studio.models import ClientProject, ProposalImage, SiteUpdatePhoto
    from website.models import PhotoCredit, PortfolioProject, Service

    used = set()
    for project in PortfolioProject.objects.all():
        apply_project(project, used, stdout)

    for service in Service.objects.all():
        key = SERVICE_PHOTOS.get(service.slug)
        if key and _set(service.image, key, f"service-{service.slug}", 1200):
            service.save()
            used.add(key)

    for project in ClientProject.objects.all():
        pool = PROPOSAL_POOL["office" if project.property_type == "office" else "default"]
        offset = 0 if project.client_id else (project.pk * 3) % len(pool)
        for i, im in enumerate(ProposalImage.objects.filter(proposal__project=project)
                               .order_by("proposal__version", "order")):
            key = pool[(offset + i) % len(pool)]
            if _set(im.image, key, f"design-{project.pk}-{im.pk}", 1200):
                im.save()
                used.add(key)
    for i, ph in enumerate(SiteUpdatePhoto.objects.order_by("pk")):
        key = SITE_POOL[i % len(SITE_POOL)]
        if _set(ph.image, key, f"site-{ph.pk}", 1200):
            ph.save()
            used.add(key)

    # Photo credits page: one row per photo actually used.
    PhotoCredit.objects.all().delete()
    for p in manifest():
        if p["key"] in used:
            PhotoCredit.objects.create(
                description=(p["title"] or p["category"].title())[:200],
                author=p["creator"][:120] or "Unknown",
                source=f"{p['source'].title()} · {p['license'].upper()}",
                url=p["landing"] or p["url"])
    return len(used)
