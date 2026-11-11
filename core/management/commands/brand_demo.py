"""Rebrand the whole demo for a prospect in one command.

    python manage.py brand_demo --name "Sharma Interiors" --city "Gwalior" --phone "+91 98260 12345" \
        --logo C:\\path\\logo.png --images C:\\path\\photos\\
"""
import re
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.branding import palette_from_logo
from core.images import optimise
from core.models import StudioSettings
from core.validators import IMAGE_EXTS

TEXT_FIELDS = ["tagline", "hero_title", "hero_subtitle", "about_text", "quotation_terms", "bank_details", "address",
               "map_embed_query"]


def _digits(phone):
    d = re.sub(r"\D", "", phone or "")
    if len(d) == 10:
        d = "91" + d
    return d


def _pretty_phone(digits):
    if len(digits) == 12 and digits.startswith("91"):
        return f"+91 {digits[2:7]} {digits[7:]}"
    return "+" + digits if digits else ""


class Command(BaseCommand):
    help = "Rebrand the demo for a prospect: name, city, contact, logo, colours and their own project photos."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help='Studio name, e.g. "Sharma Interiors"')
        parser.add_argument("--city", help="City, e.g. Gwalior")
        parser.add_argument("--phone", help="Phone number (10 digits or with +91)")
        parser.add_argument("--whatsapp", help="WhatsApp number if different from the phone")
        parser.add_argument("--email")
        parser.add_argument("--address")
        parser.add_argument("--instagram", help="Instagram handle without @")
        parser.add_argument("--tagline")
        parser.add_argument("--logo", help="Path to the logo (PNG/JPG/WebP). Colours are picked from it.")
        parser.add_argument("--color", help="Primary colour (#RRGGBB) if you don't want it picked from the logo")
        parser.add_argument("--images", help="Folder with the prospect's project photos (JPG/PNG/WebP)")
        parser.add_argument("--per-project", type=int, default=4, help="Gallery photos per portfolio project (default 4)")

    def handle(self, *args, **o):
        started = time.monotonic()
        s = StudioSettings.load()
        old_name, old_city = s.name, s.city
        name = o["name"].strip()
        if not name:
            raise CommandError("--name cannot be empty.")
        city = (o["city"] or old_city).strip()
        logo = Path(o["logo"]) if o["logo"] else None
        if logo and not logo.is_file():
            raise CommandError(f"Logo not found: {logo}")
        folder = Path(o["images"]) if o["images"] else None
        if folder and not folder.is_dir():
            raise CommandError(f"Images folder not found: {folder}")
        if o["color"] and not re.fullmatch(r"#[0-9a-fA-F]{6}", o["color"]):
            raise CommandError("--color must look like #1A73E8")

        with transaction.atomic():
            self._settings(s, o, name, city, logo)
            changed = self._replace_text(old_name, name, old_city, city)
            photos = self._photos(folder, o["per_project"]) if folder else 0
        self._reindex()

        s = StudioSettings.load()
        self.stdout.write(self.style.SUCCESS(f"Rebranded “{old_name}” → “{s.name}” in {time.monotonic() - started:.1f} s"))
        self.stdout.write(f"  City {s.city} · phone {s.phone} · WhatsApp {s.whatsapp}")
        self.stdout.write(f"  Colours: primary {s.accent_color}, secondary {s.secondary_color}, dark {s.dark_color}")
        self.stdout.write(f"  Text updated in {changed} records" + (f" · {photos} photos placed in the portfolio" if folder else ""))
        self.stdout.write("  Tip: check the homepage text and services in Studio → Website content before the call.")

    # ------------------------------------------------------------------ settings
    def _settings(self, s, o, name, city, logo):
        s.name = name
        s.legal_name = name
        s.city = city
        if o["tagline"]:
            s.tagline = o["tagline"]
        if o["phone"]:
            d = _digits(o["phone"])
            s.phone = _pretty_phone(d)
            s.whatsapp = d
        if o["whatsapp"]:
            s.whatsapp = _digits(o["whatsapp"])
        if o["email"]:
            s.email = o["email"]
        else:
            slug = re.sub(r"[^a-z0-9]", "", name.lower())[:30] or "studio"
            s.email = f"hello@{slug}.in"
        if o["instagram"] is not None:
            s.instagram = o["instagram"].lstrip("@")
        if o["address"]:
            s.address = o["address"]
            s.map_embed_query = o["address"]
        if logo:
            with logo.open("rb") as f:
                s.logo.save(f"logo-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}{logo.suffix.lower()}",
                            optimise(f, logo.name, max_px=512), save=False)
            primary, secondary, dark = palette_from_logo(str(logo))
            s.accent_color, s.secondary_color, s.dark_color = primary, secondary, dark
        if o["color"]:
            from core.branding import _from_hls  # derive matching shades from the given colour
            import colorsys
            r, g, b = (int(o["color"][i:i + 2], 16) / 255 for i in (1, 3, 5))
            h, l, sat = colorsys.rgb_to_hls(r, g, b)
            s.accent_color = o["color"].upper()
            s.secondary_color = "#{:02X}{:02X}{:02X}".format(*(round(c) for c in _from_hls((h + 0.02) % 1, min(l + 0.08, 0.6), sat)))
            s.dark_color = "#{:02X}{:02X}{:02X}".format(*(round(c) for c in _from_hls(h, 0.08, min(sat, 0.35))))
        s.save()

    # ------------------------------------------------------------------ text everywhere
    def _replace_text(self, old_name, name, old_city, city):
        from assistant.models import KnowledgeDocument
        from automations.models import AutomationLog
        from finance.models import Quotation
        from website.models import FAQ, PortfolioProject, Service

        pairs = [(old_name, name)]
        if old_city and city and old_city != city:
            pairs.append((old_city, city))
        old_first = old_name.split()[0]
        if old_first and old_first != name.split()[0] and len(old_first) > 3:
            pairs.append((old_first, name.split()[0]))   # e.g. "Aangan" in e-mail-like or short mentions

        def rep(text):
            for a, b in pairs:
                text = text.replace(a, b)
            return text

        s = StudioSettings.load()
        for f in TEXT_FIELDS:
            setattr(s, f, rep(getattr(s, f)))
        s.save()

        changed = 0
        targets = [(Service, ["short", "description"]), (FAQ, ["question", "answer"]),
                   (PortfolioProject, ["location", "summary", "description", "brief"]),
                   (KnowledgeDocument, ["title", "content"]), (AutomationLog, ["message"]),
                   (Quotation, ["terms", "notes"])]
        for model, fields in targets:
            for obj in model.objects.all():
                dirty = [f for f in fields if rep(getattr(obj, f) or "") != (getattr(obj, f) or "")]
                if dirty:
                    for f in dirty:
                        setattr(obj, f, rep(getattr(obj, f)))
                    model.objects.filter(pk=obj.pk).update(**{f: getattr(obj, f) for f in dirty})
                    changed += 1
        return changed

    # ------------------------------------------------------------------ the prospect's own photos
    def _photos(self, folder, per_project):
        from website.models import PhotoCredit, PortfolioProject, ProjectImage

        files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower().lstrip(".") in IMAGE_EXTS)
        if not files:
            raise CommandError(f"No JPG/PNG/WebP photos found in {folder}")
        projects = list(PortfolioProject.objects.order_by("-is_featured", "order", "id"))
        if not projects:
            raise CommandError("There are no portfolio projects yet — run seed_demo first.")
        per_project = max(1, min(per_project, 12))
        placed, i = 0, 0
        for p in projects:
            chosen = [files[(i + k) % len(files)] for k in range(min(per_project, len(files)))]
            i += len(chosen)
            with chosen[0].open("rb") as f:
                p.cover.save(chosen[0].name, optimise(f, chosen[0].name), save=True)
            for img in p.images.all():
                img.image.delete(save=False)
            p.images.all().delete()
            for order, path in enumerate(chosen):
                with path.open("rb") as f:
                    ProjectImage.objects.create(project=p, image=optimise(f, path.name), order=order,
                                                room=p.get_room_type_display(), caption="")
                placed += 1
        PhotoCredit.objects.get_or_create(description="Portfolio project photos", author=StudioSettings.load().name,
                                          source="Studio's own work")
        return placed

    def _reindex(self):
        try:
            from assistant import rag
            from assistant.sync import sync_all
            sync_all()
            rag.reindex_all()
        except Exception as e:  # never fail the rebrand because of the AI index
            self.stdout.write(self.style.WARNING(f"AI index will rebuild on first use ({e})."))
