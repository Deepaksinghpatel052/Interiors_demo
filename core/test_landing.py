from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import ProductEnquiry, StudioSettings

P = "/"
VALID = {"name": "Rohit Sharma", "mobile": "+91 98260 12345", "studio_name": "Sharma Interiors", "city": "Gwalior",
         "email": "", "team_size": "2_5", "modules": ["erp", "ai"], "contact_pref": "whatsapp", "message": "Excel quotes"}


@override_settings(DEMO_MODE=True, LANDING_PAGE=True, CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                                                       "LOCATION": "landing-tests"}})
class LandingTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_root_is_the_product_landing_and_studio_site_moves(self):
        r = self.client.get(reverse("website:home"))
        self.assertEqual(reverse("website:home"), "/demo/")
        self.assertTemplateUsed(r, "website/home.html")
        self.assertRedirects(self.client.get("/product/"), "/", fetch_redirect_response=False)
        r = self.client.get(P)
        self.assertTemplateUsed(r, "core/landing.html")
        self.assertContains(r, 'id="enquire"')
        self.assertContains(r, "Explore the live demo")
        self.assertNotContains(r, "demo-ribbon")

    def test_enquiry_is_saved(self):
        r = self.client.post(P, VALID)
        self.assertRedirects(r, P + "?sent=1#enquire-form", fetch_redirect_response=False)
        e = ProductEnquiry.objects.get()
        self.assertEqual((e.mobile, e.modules, e.status), ("9826012345", ["erp", "ai"], "new"))
        self.assertEqual(e.modules_display, "Studio ERP, AI assistant")
        self.assertContains(self.client.get(P + "?sent=1"), "Thank you, Rohit!")

    def test_validation_honeypot_and_rate_limit(self):
        r = self.client.post(P, {**VALID, "mobile": "12345"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "valid 10-digit")
        self.assertContains(r, 'value="erp"')
        self.client.post(P, {**VALID, "website": "http://spam"})
        self.assertFalse(ProductEnquiry.objects.exists())
        cache.clear()
        for _ in range(5):
            self.client.post(P, VALID)
        self.client.post(P, VALID)
        self.assertEqual(ProductEnquiry.objects.count(), 5)

    def test_module_preselected_from_package_link(self):
        r = self.client.get(P + "?module=erp")
        self.assertRegex(r.content.decode(), r'value="erp" id="[^"]+" checked')

    def test_admin_lists_and_exports_enquiries(self):
        self.client.post(P, VALID)
        admin = User.objects.create_superuser("boss", "b@example.com", "pw12345!x")
        self.client.force_login(admin)
        r = self.client.get(reverse("admin:core_productenquiry_changelist"))
        self.assertContains(r, "Sharma Interiors")
        self.assertContains(r, "wa.me/919826012345")
        r = self.client.post(reverse("admin:core_productenquiry_changelist"),
                             {"action": "export_csv", "_selected_action": [ProductEnquiry.objects.get().pk]})
        self.assertIn("Rohit Sharma", r.content.decode("utf-8-sig"))
        self.assertIn(ProductEnquiry, site._registry)

    def test_landing_survives_website_module_off(self):
        s = StudioSettings.load()
        s.module_website = False
        s.save()
        self.assertEqual(self.client.get(P).status_code, 200)


@override_settings(DEMO_MODE=False)
class ClientSiteTests(TestCase):
    def test_root_is_the_studio_home_on_a_client_site(self):
        r = self.client.get("/")
        self.assertTemplateUsed(r, "website/home.html")
        self.assertNotContains(r, 'id="enquire"')
        self.assertRedirects(self.client.get("/demo/"), "/", fetch_redirect_response=False)
        self.client.post("/", VALID)                       # no enquiry form on client sites
        self.assertFalse(ProductEnquiry.objects.exists())

    def test_links_point_to_root(self):
        self.assertContains(self.client.get("/"), 'class="brand" href="/"')
