import io
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.branding import DEFAULT, contrast_with_white, palette_from_logo
from core.demo_reset import wipe
from core.models import StudioSettings
from core.permissions import CLIENT, OWNER, TEAM
from crm.models import Lead
from website.models import FAQ, PortfolioProject, ProjectImage, Service, Testimonial


def user(name, group, **kw):
    u = User.objects.create_user(username=name, password="pw12345!", **kw)
    u.groups.add(Group.objects.get_or_create(name=group)[0])
    return u


def png_bytes(color=(200, 30, 40), size=(120, 80), mode="RGB"):
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, "PNG")
    return buf.getvalue()


def project(title="Calm 3 BHK"):
    return PortfolioProject.objects.create(
        title=title, location="Vijay Nagar, Indore", room_type="full_home", style="modern", budget_band="8_15",
        summary="A calm home in Indore", description="Designed by Aangan Interiors in Indore.",
        cover=SimpleUploadedFile("c.png", png_bytes(), content_type="image/png"))


class PaletteTests(TestCase):
    def test_brand_colour_from_logo_is_readable(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "logo.png").write_bytes(png_bytes((230, 120, 20)))     # bright orange: too light for white text
        primary, secondary, dark = palette_from_logo(str(tmp / "logo.png"))
        rgb = tuple(int(primary[i:i + 2], 16) for i in (1, 3, 5))
        self.assertGreater(rgb[0], rgb[2])                              # still orange-ish
        self.assertGreaterEqual(contrast_with_white(rgb), 3.2)
        self.assertNotEqual(primary, DEFAULT[0])

    def test_grey_or_transparent_logo_keeps_default(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "grey.png").write_bytes(png_bytes((128, 128, 128)))
        (tmp / "clear.png").write_bytes(png_bytes((0, 0, 0, 0), mode="RGBA"))
        self.assertEqual(palette_from_logo(str(tmp / "grey.png")), DEFAULT)
        self.assertEqual(palette_from_logo(str(tmp / "clear.png")), DEFAULT)


class BrandDemoTests(TestCase):
    def test_rebrands_settings_text_and_photos(self):
        p = project()
        ProjectImage.objects.create(project=p, image=SimpleUploadedFile("g.png", png_bytes(), content_type="image/png"))
        faq = FAQ.objects.create(question="Do you work outside Indore?", answer="Aangan Interiors works across Indore.")
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "logo.png").write_bytes(png_bytes((20, 120, 60)))
        photos = tmp / "photos"
        photos.mkdir()
        for i in range(3):
            (photos / f"site{i}.jpg").write_bytes(png_bytes((40 * i, 90, 120)))   # PNG data, .jpg name: Pillow copes
        (photos / "notes.txt").write_text("ignore me")
        out = io.StringIO()
        call_command("brand_demo", name="Sharma Interiors", city="Gwalior", phone="9826012345",
                     logo=str(tmp / "logo.png"), images=str(photos), per_project=2, stdout=out)
        s = StudioSettings.load()
        self.assertEqual((s.name, s.city, s.whatsapp, s.phone), ("Sharma Interiors", "Gwalior", "919826012345", "+91 98260 12345"))
        self.assertTrue(s.logo.name.startswith("brand/"))
        self.assertNotEqual(s.accent_color, "#0081F6")
        faq.refresh_from_db()
        self.assertEqual(faq.answer, "Sharma Interiors works across Gwalior.")
        p.refresh_from_db()
        self.assertEqual(p.location, "Vijay Nagar, Gwalior")
        self.assertEqual(p.images.count(), 2)
        self.assertIn("Rebranded", out.getvalue())

    def test_bad_arguments(self):
        with self.assertRaises(CommandError):
            call_command("brand_demo", name="X", logo="no/such/logo.png", stdout=io.StringIO())
        with self.assertRaises(CommandError):
            call_command("brand_demo", name="X", color="blue", stdout=io.StringIO())


class ResetAndSetupTests(TestCase):
    def setUp(self):
        self.admin = user("admin", OWNER, is_superuser=True, is_staff=True)
        self.seller = User.objects.create_superuser("devnix", "d@example.com", "pw12345!x")
        user("owner", OWNER)
        user("designer", TEAM)
        user("c9876543210", CLIENT)
        Lead.objects.create(name="Asha", mobile="9876500000")
        Service.objects.create(title="Turnkey", slug="turnkey", short="s", description="d")
        Testimonial.objects.create(name="Sample person", text="Lovely", is_sample=True)
        Testimonial.objects.create(name="Real person", text="Great", is_sample=False)

    @override_settings(DEMO_MODE=False)
    def test_reset_refuses_on_live_site(self):
        with self.assertRaises(CommandError):
            call_command("reset_demo", stdout=io.StringIO())
        self.assertEqual(Lead.objects.count(), 1)

    def test_wipe_for_reset_keeps_seller_superuser(self):
        wipe()
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(Service.objects.exists())
        self.assertEqual(list(User.objects.values_list("username", flat=True)), ["devnix"])

    def test_setup_client(self):
        StudioSettings.objects.filter(pk=1).update(name="Sharma Interiors")
        with mock.patch("core.management.commands.setup_client.set_env") as env:
            env.return_value = Path(".env")
            out = io.StringIO()
            call_command("setup_client", owner_username="rohit", owner_name="Rohit Sharma", keep_content=True,
                         noinput=True, stdout=out)
        env.assert_called_once_with("DEMO_MODE", "False")
        names = set(User.objects.values_list("username", flat=True))
        self.assertEqual(names, {"devnix", "rohit"})
        rohit = User.objects.get(username="rohit")
        self.assertTrue(rohit.groups.filter(name=OWNER).exists())
        self.assertEqual(rohit.first_name, "Rohit")
        self.assertIn("Generated password", out.getvalue())
        self.assertFalse(Lead.objects.exists())
        self.assertTrue(Service.objects.exists())                       # --keep-content
        self.assertEqual(list(Testimonial.objects.values_list("name", flat=True)), ["Real person"])
        self.assertEqual(StudioSettings.load().name, "Sharma Interiors")

    def test_setup_client_rejects_demo_username_and_weak_password(self):
        with self.assertRaises(CommandError):
            call_command("setup_client", owner_username="owner", noinput=True, stdout=io.StringIO())
        with self.assertRaises(CommandError):
            call_command("setup_client", owner_username="rohit", password="123", noinput=True, stdout=io.StringIO())
        self.assertTrue(Lead.objects.exists())                          # nothing deleted


class ModuleFlagTests(TestCase):
    def setUp(self):
        self.owner = user("own", OWNER)
        self.client.force_login(self.owner)

    def off(self, **flags):
        s = StudioSettings.load()
        for k, v in flags.items():
            setattr(s, "module_" + k, v)
        s.save()

    def test_erp_off(self):
        self.off(erp=False)
        self.assertRedirects(self.client.get(reverse("studio:dashboard")), reverse("cms:index"))
        r = self.client.get(reverse("studio:leads"))
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "not part of this package", status_code=404)
        self.assertEqual(self.client.get(reverse("finance:quotations")).status_code, 404)
        self.assertEqual(self.client.get(reverse("studio:settings")).status_code, 200)
        page = self.client.get(reverse("cms:index"))
        self.assertNotContains(page, 'href="%s"' % reverse("studio:leads"))
        self.assertContains(page, 'data-locked="module_erp"')

    @override_settings(LANDING_PAGE=True)
    def test_website_portal_ai_automation_off(self):
        self.off(website=False, portal=False, ai=False, automation=False)
        self.client.logout()
        self.assertRedirects(self.client.get(reverse("website:home")), reverse("core:login"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("landing")).status_code, 200)   # the product page stays up
        self.assertEqual(self.client.get(reverse("website:portfolio")).status_code, 404)
        self.assertEqual(self.client.get(reverse("bookings:book")).status_code, 404)
        r = self.client.post(reverse("assistant:public_chat"), "{}", content_type="application/json")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["error"], "This module is not part of this package.")
        Lead.objects.create(name="No automation", mobile="9000000000")
        from automations.models import AutomationLog
        self.assertFalse(AutomationLog.objects.exists())
        self.client.force_login(user("cl", CLIENT))
        self.assertEqual(self.client.get(reverse("portal:overview")).status_code, 404)

    def test_teasers_hidden_when_switched_off(self):
        s = StudioSettings.load()
        s.module_erp, s.show_locked_teasers = False, False
        s.save()
        self.assertNotContains(self.client.get(reverse("cms:index")), "data-locked=")


class ReportTests(TestCase):
    def setUp(self):
        self.client.force_login(user("own", OWNER))
        Lead.objects.create(name="=HYPERLINK(\"x\")", mobile="9000000001", source="instagram", stage="won")
        Lead.objects.create(name="Ravi", mobile="9000000002", source="instagram", stage="lost")
        Lead.objects.create(name="Meera", mobile="9000000003", source="website")

    def test_report_page(self):
        r = self.client.get(reverse("studio:reports"), {"months": "3"})
        self.assertEqual(r.context["summary"]["leads"], 3)
        self.assertEqual(r.context["summary"]["conversion"], 33.3)
        insta = [x for x in r.context["sources"] if x["source"] == "Instagram"][0]
        self.assertEqual((insta["leads"], insta["won"], insta["conversion"]), (2, 1, 50.0))

    def test_csv_exports_are_safe(self):
        for kind in ["leads", "sources", "revenue", "outstanding", "payments"]:
            r = self.client.get(reverse("studio:report_csv", args=[kind]))
            self.assertEqual(r.status_code, 200, kind)
            self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        body = self.client.get(reverse("studio:report_csv", args=["leads"])).content.decode("utf-8-sig")
        self.assertIn("'=HYPERLINK", body)
        self.assertEqual(self.client.get(reverse("studio:report_csv", args=["secrets"])).status_code, 404)

    def test_client_cannot_see_reports(self):
        self.client.force_login(user("cl", CLIENT))
        self.assertEqual(self.client.get(reverse("studio:reports")).status_code, 403)


class CmsTests(TestCase):
    def setUp(self):
        self.client.force_login(user("own", OWNER))

    def test_team_member_cannot_edit_website(self):
        self.client.force_login(user("tm", TEAM))
        self.assertEqual(self.client.get(reverse("cms:index")).status_code, 403)
        self.assertEqual(self.client.get(reverse("cms:list", args=["services"])).status_code, 403)

    def test_homepage_text(self):
        r = self.client.post(reverse("cms:index"), {"tagline": "Warm homes", "hero_title": "Hello Gwalior",
                                                     "hero_subtitle": "Sub", "about_text": "About", "founded_year": 2015})
        self.assertRedirects(r, reverse("cms:index"))
        self.assertEqual(StudioSettings.load().hero_title, "Hello Gwalior")

    def test_service_crud_and_unknown_kind(self):
        r = self.client.post(reverse("cms:new", args=["services"]), {"title": "Kitchen design", "icon": "house",
                                                                       "short": "Modular kitchens", "description": "We design kitchens.",
                                                                       "order": 1, "is_active": "on"})
        self.assertRedirects(r, reverse("cms:list", args=["services"]))
        svc = Service.objects.get(title="Kitchen design")
        self.assertEqual(svc.slug, "kitchen-design")
        self.client.post(reverse("cms:delete", args=["services", svc.pk]))
        self.assertFalse(Service.objects.filter(pk=svc.pk).exists())
        self.assertEqual(self.client.get(reverse("cms:list", args=["users"])).status_code, 404)

    def test_project_photos_upload_validate_and_cover(self):
        p = project()
        good = SimpleUploadedFile("room.png", png_bytes(size=(2400, 1600)), content_type="image/png")
        bad = SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png")
        self.client.post(reverse("cms:project_media", args=[p.pk]), {"action": "upload", "images": [good, bad]})
        self.assertEqual(p.images.count(), 1)
        img = p.images.get()
        with Image.open(img.image.path) as im:
            self.assertLessEqual(max(im.size), 1800)                    # resized for fast pages
        self.client.post(reverse("cms:project_media", args=[p.pk]), {"action": "cover", "image": img.pk})
        self.client.post(reverse("cms:project_media", args=[p.pk]), {"action": "save", f"caption-{img.pk}": "Living room",
                                                                     f"order-{img.pk}": "3"})
        img.refresh_from_db()
        self.assertEqual((img.caption, img.order, img.in_mood_board), ("Living room", 3, False))

    def test_moodboard_formsets(self):
        p = project()
        data = {"rooms-TOTAL_FORMS": "1", "rooms-INITIAL_FORMS": "0", "rooms-MIN_NUM_FORMS": "0", "rooms-MAX_NUM_FORMS": "1000",
                "rooms-0-name": "Living", "rooms-0-description": "Warm wood", "rooms-0-order": "0",
                "sw-TOTAL_FORMS": "1", "sw-INITIAL_FORMS": "0", "sw-MIN_NUM_FORMS": "0", "sw-MAX_NUM_FORMS": "1000",
                "sw-0-kind": "colour", "sw-0-name": "Sage", "sw-0-hex": "#9CAF88", "sw-0-note": "", "sw-0-order": "0"}
        r = self.client.post(reverse("cms:project_moodboard", args=[p.pk]), data)
        self.assertRedirects(r, reverse("cms:project_moodboard", args=[p.pk]))
        self.assertEqual(p.rooms.get().name, "Living")
        self.assertEqual(p.swatches.get().hex, "#9CAF88")
