"""Seed the demo with Aangan Interiors content.

Phase 1 seeds: studio settings, demo users, services, FAQs, sample testimonials and
10 portfolio projects with generated images. Later phases extend this command.
"""
import random
from datetime import time, timedelta

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core import demo_data as D
from core.demo_more_designs import MORE_ROOMS
from core.demo_images import room_image, to_jpeg_bytes, to_thumb
from bookings.models import BlockedDate, Booking, WeeklyAvailability
from core.models import StudioSettings
from core.seed_erp import seed_erp
from core.seed_finance import seed_finance
from core.seed_automations import seed_automations
from core.seed_knowledge import seed_knowledge
from core.seed_sales import seed_packages
from core.seed_portal import seed_portal
from crm.models import Lead, LeadActivity
from website.models import (FAQ, BeforeAfter, PortfolioProject, ProjectImage, ProjectRoom,
                            ProjectSwatch, Service, Testimonial, TimelineStep)

USERS = [
    # username, password, first, last, group, is_staff, is_superuser
    ("admin", "admin12345", "Studio", "Admin", "Owner", True, True),
    ("owner", "demo12345", "Ananya", "Mehta", "Owner", True, False),
    ("designer", "demo12345", "Kabir", "Joshi", "Team Member", True, False),
    ("client", "demo12345", "Rahul", "Verma", "Client", False, False),
]

GALLERY_ROOMS = {
    "full_home": ["living", "bedroom", "kitchen", "living"],
    "living": ["living", "living", "living"],
    "bedroom": ["bedroom", "bedroom", "bedroom"],
    "kitchen": ["kitchen", "kitchen", "kitchen"],
    "office": ["office", "office", "office"],
    "retail": ["retail", "retail", "retail"],
}


class Command(BaseCommand):
    help = "Seed demo data for the Aangan Interiors demo studio."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing demo content first.")
        parser.add_argument("--offline", action="store_true",
                            help="Don't download real photos; use the generated illustrations only.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["flush"]:
            self.flush()
        StudioSettings.load().save()  # ensures the singleton exists
        self.seed_users()
        self.seed_services()
        self.seed_faqs()
        self.seed_testimonials()
        self.seed_portfolio()
        self.seed_availability()
        self.seed_bookings()
        seed_erp(self.stdout)
        seed_finance(self.stdout)
        self.seed_photos(offline=opts["offline"])
        seed_portal(self.stdout)
        seed_knowledge(self.stdout, StudioSettings.load())
        seed_automations(self.stdout)
        seed_packages(self.stdout)
        self.seed_tour()
        self.stdout.write(self.style.SUCCESS("Demo data ready. Logins: owner / designer / client  (demo12345), admin / admin12345"))

    # ------------------------------------------------------------------
    def flush(self):
        from assistant.models import ChatSession, KnowledgeDocument
        from automations.models import AutomationLog
        AutomationLog.objects.all().delete()
        from finance.models import CatalogueItem, Quotation, Vendor
        from studio.models import ClientProject
        for model in (ChatSession, KnowledgeDocument, Quotation, CatalogueItem, Vendor, ClientProject, Booking, LeadActivity, Lead, BlockedDate, WeeklyAvailability,
                      PortfolioProject, Service, FAQ, Testimonial):
            model.objects.all().delete()
        self.stdout.write("Flushed demo content.")

    def seed_tour(self):
        """Sample 360° house tour (only visible once the extra feature is switched on)."""
        from website.models import Tour, TourHotspot, TourRoom
        from website.tour360 import seed_sample_tour
        t = seed_sample_tour(Tour, TourRoom, TourHotspot)
        self.stdout.write("360° tour (sample): " + (f"{t.title}, {t.rooms.count()} rooms" if t else "kept existing"))

    def seed_users(self):
        for username, pw, first, last, group, staff, su in USERS:
            g, _ = Group.objects.get_or_create(name=group)
            u, created = User.objects.get_or_create(username=username)
            u.first_name, u.last_name = first, last
            u.email = f"{username}@example.com"
            u.is_staff, u.is_superuser = staff, su
            u.set_password(pw)
            u.save()
            u.groups.set([g])
        self.stdout.write(f"Users: {', '.join(u[0] for u in USERS)}")

    def seed_services(self):
        for i, (title, slug, icon, short, desc, includes, timeline) in enumerate(D.SERVICES):
            Service.objects.update_or_create(slug=slug, defaults=dict(
                title=title, icon=icon, short=short, description=desc, includes=includes,
                typical_timeline=timeline, order=i))
        self.stdout.write(f"Services: {len(D.SERVICES)}")

    def seed_faqs(self):
        for i, (cat, q, a) in enumerate(D.FAQS):
            FAQ.objects.update_or_create(question=q, defaults=dict(answer=a, category=cat, order=i))
        self.stdout.write(f"FAQs: {len(D.FAQS)}")

    def seed_testimonials(self):
        for i, (name, city, ptype, text) in enumerate(D.TESTIMONIALS):
            Testimonial.objects.update_or_create(name=name, defaults=dict(
                city=city, project_type=ptype, text=text, is_sample=True, order=i))
        self.stdout.write(f"Testimonials (sample): {len(D.TESTIMONIALS)}")

    def _save_image(self, field, name, img, thumb=False):
        if thumb:
            img = to_thumb(img, 1000)
        field.save(name, ContentFile(to_jpeg_bytes(img)), save=False)

    def seed_portfolio(self, rows=None, start=0):
        """Create the portfolio projects in `rows` (default: all of demo_data.PROJECTS) that don't exist yet."""
        rnd = random.Random(42)
        for i, row in enumerate(D.PROJECTS if rows is None else rows, start):
            (title, room, style, budget, prop, area, weeks, location, featured, summary, brief) = row
            if PortfolioProject.objects.filter(title=title).exists():
                continue
            seed = 1000 + i * 17
            p = PortfolioProject(
                title=title, room_type=room, style=style, budget_band=budget, property_type=prop,
                area_sqft=area, duration_weeks=weeks, location=location, is_featured=featured,
                year=2022 + i % 4, order=i, summary=summary, brief=brief,
                description=(
                    f"We began with a detailed site survey and a conversation about daily routines. "
                    f"The {dict(PortfolioProject._meta.get_field('style').choices)[style].lower()} direction "
                    f"came from the family's own references, refined into a palette of a few honest materials.\n\n"
                    f"Layouts were shared in the client portal in two versions; the approved version balanced "
                    f"storage with open floor space. Execution was supervised daily, with photo updates every week "
                    f"and a snag list closed before handover."),
                client_quote=D.QUOTES[i % len(D.QUOTES)] if i % 2 == 0 else "",
                client_name="Homeowner" if room not in ("office", "retail") else "Business owner",
            )
            self._save_image(p.cover, f"{slugify(title)}-cover.jpg", room_image(style, room, seed))
            p.save()

            for j, groom in enumerate(GALLERY_ROOMS[room]):
                im = ProjectImage(project=p, caption=f"{dict(ROOM_LABELS).get(groom, groom.title())} view {j + 1}",
                                  room=groom, order=j)
                self._save_image(im.image, f"{p.slug}-{j}.jpg", room_image(style, groom, seed + j + 1), thumb=True)
                im.save()

            ba = BeforeAfter(project=p, caption="Same room, same angle — before work started and at handover.")
            self._save_image(ba.before, f"{p.slug}-before.jpg", room_image(style, room, seed, empty=True), thumb=True)
            self._save_image(ba.after, f"{p.slug}-after.jpg", room_image(style, room, seed), thumb=True)
            ba.save()

            for k, (name, desc) in enumerate(MORE_ROOMS.get(title) or D.ROOMS_BY_TYPE[room]):
                ProjectRoom.objects.create(project=p, name=name, description=desc, order=k)
            for k, (name, hex_) in enumerate(D.COLOURS_BY_STYLE[style]):
                ProjectSwatch.objects.create(project=p, kind="colour", name=name, hex=hex_, order=k)
            for k, (name, hex_, note) in enumerate(D.MATERIALS_BY_STYLE[style]):
                ProjectSwatch.objects.create(project=p, kind="material", name=name, hex=hex_, note=note, order=k)

            design_w = max(2, weeks // 4)
            steps = [("Consultation & site visit", "Week 1", "Brief, measurements and photos."),
                     ("Design & 3D", f"Week 2–{1 + design_w}", "Two layout options, mood board, 3D views."),
                     ("Approvals & ordering", f"Week {2 + design_w}", "Materials locked, orders placed."),
                     ("Execution", f"Week {3 + design_w}–{weeks - 1}", "Carpentry, ceiling, painting, fittings."),
                     ("Handover", f"Week {weeks}", "Deep cleaning, styling and walkthrough.")]
            for k, (t, dur, desc) in enumerate(steps):
                TimelineStep.objects.create(project=p, title=t, duration=dur, description=desc, order=k)
            rnd.random()
            self.stdout.write(f"  · {p.title}")
        self.stdout.write(f"Portfolio projects: {PortfolioProject.objects.count()}")


    def seed_photos(self, offline=False):
        from core import photos
        if not offline:
            ok, failed = photos.fetch()
            if failed:
                self.stdout.write(self.style.WARNING(f"{len(failed)} photos could not be downloaded; illustrations kept."))
        used = photos.apply()
        self.stdout.write(f"Real photos applied: {used}")

    def seed_availability(self):
        if WeeklyAvailability.objects.exists():
            return
        for wd in range(6):  # Monday–Saturday; Sunday closed
            WeeklyAvailability.objects.create(weekday=wd, start_time=time(10, 0), end_time=time(13, 0))
            WeeklyAvailability.objects.create(weekday=wd, start_time=time(15, 0), end_time=time(19, 0))
        # Block one upcoming weekday (e.g. a studio offsite) so the demo shows blocked dates.
        d = timezone.localdate() + timedelta(days=9)
        while d.weekday() == 6:
            d += timedelta(days=1)
        BlockedDate.objects.get_or_create(date=d, defaults={"reason": "Studio offsite"})
        self.stdout.write("Availability: Mon–Sat 10–1 & 3–7, one blocked date")

    def seed_bookings(self):
        if Booking.objects.exists():
            return
        rnd = random.Random(7)
        owner = User.objects.filter(username="owner").first()
        designer = User.objects.filter(username="designer").first()
        slots = [time(10), time(11), time(12), time(15), time(16), time(17), time(18)]
        today = timezone.localdate()
        blocked = set(BlockedDate.objects.values_list("date", flat=True))
        made, day_offset = 0, 1
        while made < len(D.BOOKING_PEOPLE) and day_offset < 21:
            day = today + timedelta(days=day_offset)
            day_offset += 1
            if day.weekday() == 6 or day in blocked:
                continue
            for t in rnd.sample(slots, k=rnd.choice([1, 1, 2])):
                if made >= len(D.BOOKING_PEOPLE):
                    break
                name, mobile, city, prop, budget, mode, note = D.BOOKING_PEOPLE[made]
                lead = Lead.objects.create(
                    name=name, mobile=mobile, city=city, source=rnd.choice(["website", "instagram", "referral", "website"]),
                    stage=Lead.Stage.SITE_VISIT if mode == "site_visit" else Lead.Stage.CONSULTATION,
                    property_type=prop, budget_band=budget, message=note,
                    assigned_to=owner if made % 2 else designer)
                b = Booking.objects.create(
                    lead=lead, mode=mode, date=day, start_time=t, name=name, mobile=mobile,
                    kind=Booking.Kind.SITE_VISIT if mode == "site_visit" else Booking.Kind.CONSULTATION,
                    site_address=f"{city}" if mode == "site_visit" else "", notes=note,
                    assigned_to=lead.assigned_to)
                LeadActivity.objects.create(lead=lead, text=f"Booked {b.get_mode_display().lower()} for "
                                                            f"{day:%d-%m-%Y} at {t:%I:%M %p} ({b.reference})")
                made += 1
        self.stdout.write(f"Bookings (next 2–3 weeks): {made}")


ROOM_LABELS = [("living", "Living room"), ("bedroom", "Bedroom"), ("kitchen", "Kitchen"),
               ("office", "Workspace"), ("retail", "Store")]
