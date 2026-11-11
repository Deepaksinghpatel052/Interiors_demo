from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import StudioSettings
from core.templatetags.studio import format_inr, inr_short, wa_link
from crm.models import Lead

from .models import PortfolioProject

TINY_JPG = (b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9")


class IndianFormatTests(TestCase):
    def test_inr_grouping(self):
        self.assertEqual(format_inr(125000), "₹1,25,000")
        self.assertEqual(format_inr(12500000), "₹1,25,00,000")
        self.assertEqual(format_inr(999), "₹999")
        self.assertEqual(format_inr(0), "₹0")
        self.assertEqual(format_inr(-4500), "−₹4,500")
        self.assertEqual(format_inr("1234567.5", decimals=2), "₹12,34,567.50")

    def test_inr_short(self):
        self.assertEqual(inr_short(450000), "₹4.5L")
        self.assertEqual(inr_short(12000000), "₹1.2Cr")
        self.assertEqual(inr_short(500000), "₹5L")

    def test_whatsapp_link(self):
        self.assertEqual(wa_link("+91 98270 00000", "Hi there"), "https://wa.me/919827000000?text=Hi%20there")


class StudioSettingsTests(TestCase):
    def test_singleton(self):
        a = StudioSettings.load()
        a.name = "Sharma Interiors"
        a.save()
        StudioSettings(name="Another").save()
        self.assertEqual(StudioSettings.objects.count(), 1)

    def test_rebrand_shows_everywhere(self):
        s = StudioSettings.load()
        s.name = "Sharma Interiors"
        s.save()
        self.assertContains(self.client.get("/"), "Sharma Interiors")


class PublicPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1 = PortfolioProject.objects.create(
            title="Teal Living", room_type="living", style="modern", budget_band="5_10", location="Indore",
            summary="s", description="d", cover=SimpleUploadedFile("a.jpg", TINY_JPG, "image/jpeg"), is_featured=True)
        cls.p2 = PortfolioProject.objects.create(
            title="Haveli Bedroom", room_type="bedroom", style="traditional", budget_band="10_20", location="Gwalior",
            summary="s", description="d", cover=SimpleUploadedFile("b.jpg", TINY_JPG, "image/jpeg"))

    def test_pages_load(self):  # noqa
        self.assertEqual(self.client.get("/").status_code, 200)   # studio home
        for name in ["portfolio", "services", "about", "contact", "faq", "privacy", "credits", "thanks", "quiz", "estimate"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"website:{name}")).status_code, 200)
        self.assertEqual(self.client.get(self.p1.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(reverse("core:login")).status_code, 200)

    def test_unpublished_project_404(self):
        self.p2.is_published = False
        self.p2.save()
        self.assertEqual(self.client.get(self.p2.get_absolute_url()).status_code, 404)

    def test_portfolio_filter_marks_hidden(self):
        r = self.client.get(reverse("website:portfolio") + "?style=traditional")
        self.assertEqual(r.context["visible_count"], 1)
        visible = [p.title for p in r.context["projects"] if p.visible]
        self.assertEqual(visible, ["Haveli Bedroom"])

    def test_portfolio_ignores_bad_filter(self):
        r = self.client.get(reverse("website:portfolio") + "?style=<script>")
        self.assertEqual(r.context["visible_count"], 2)

    def test_slug_unique(self):
        p = PortfolioProject.objects.create(
            title="Teal Living", room_type="living", style="modern", budget_band="5_10", location="Indore",
            summary="s", description="d", cover=SimpleUploadedFile("c.jpg", TINY_JPG, "image/jpeg"))
        self.assertEqual(p.slug, "teal-living-2")


class EnquiryTests(TestCase):
    def test_enquiry_creates_lead(self):
        r = self.client.post(reverse("website:contact"), {
            "name": "Neha Sharma", "mobile": "+91 98765 43210", "email": "", "property_type": "2bhk",
            "budget_band": "5_10", "style_preference": "modern", "message": "Living room", "website": ""})
        self.assertRedirects(r, reverse("website:thanks"))
        lead = Lead.objects.get()
        self.assertEqual(lead.mobile, "9876543210")
        self.assertEqual(lead.source, "website")
        self.assertEqual(lead.activities.count(), 1)
        self.assertContains(self.client.get(reverse("website:thanks")), "Neha Sharma")

    def test_invalid_mobile_rejected(self):
        r = self.client.post(reverse("website:contact"), {"name": "Test", "mobile": "12345"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Lead.objects.exists())
        self.assertContains(r, "valid 10-digit")

    def test_honeypot_blocks_spam(self):
        self.client.post(reverse("website:contact"), {"name": "Bot", "mobile": "9876543210", "website": "spam.com"})
        self.assertFalse(Lead.objects.exists())

    def test_user_input_escaped(self):
        self.client.post(reverse("website:contact"), {"name": "<script>x</script>", "mobile": "9876543210"})
        r = self.client.get(reverse("website:thanks"))
        self.assertNotContains(r, "<script>x</script>")
        self.assertContains(r, "&lt;script&gt;")
