"""Phase 9 quality pass: accessibility and mobile fixes that should not regress."""
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings

from studio.forms import AvailabilityFormSet
from website.cms import _style_formset
from website.cms_forms import SwatchFormSet


class Phase9Tests(TestCase):
    def test_formset_rows_have_accessible_names(self):
        form = AvailabilityFormSet(queryset=AvailabilityFormSet.model.objects.none()).forms[0]
        for name in ("weekday", "start_time", "end_time"):
            self.assertIn("aria-label", form.fields[name].widget.attrs, name)

    def test_cms_swatch_rows_have_accessible_names(self):
        form = _style_formset(SwatchFormSet(prefix="sw")).forms[0]
        self.assertEqual(form.fields["hex"].widget.attrs.get("aria-label"), str(form.fields["hex"].label))

    def test_client_ip_trusts_x_real_ip_only_behind_own_nginx(self):
        from django.test import RequestFactory
        from core.ratelimit import client_ip
        req = RequestFactory().get("/", REMOTE_ADDR="172.18.0.1", HTTP_X_REAL_IP="203.0.113.7",
                                   HTTP_X_FORWARDED_FOR="1.2.3.4")
        with self.settings(TRUST_X_REAL_IP=False):
            self.assertEqual(client_ip(req), "172.18.0.1")
        with self.settings(TRUST_X_REAL_IP=True):
            self.assertEqual(client_ip(req), "203.0.113.7")   # X-Forwarded-For is never used

    @override_settings(DEMO_MODE=True, LANDING_PAGE=False)
    def test_landing_switched_off_home_is_the_studio_site(self):
        r = self.client.get("/")
        self.assertTemplateUsed(r, "website/home.html")
        self.assertNotContains(r, 'id="enquiryForm"')
        self.assertRedirects(self.client.get("/demo/"), "/", fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/product/"), "/", fetch_redirect_response=False)
        self.assertContains(r, "demo-ribbon")   # still a demo: ribbon and tour stay

    @override_settings(DEMO_MODE=True, LANDING_PAGE=False)
    def test_landing_off_tour_starts_at_root(self):
        from core.tour import steps
        self.assertEqual(steps()[0]["url"], "/")

    @override_settings(DEMO_MODE=True, LANDING_PAGE=True)
    def test_enquiry_form_and_errors_land_on_form_card(self):
        html = self.client.get("/").content.decode()
        self.assertIn('id="enquire-form"', html)
        self.assertIn('action="/#enquire-form"', html)

    def test_estimate_area_input_is_labelled(self):
        self.assertContains(self.client.get("/estimate/"), 'aria-label="Carpet area in square feet"')

    def test_studio_header_can_truncate_long_titles(self):
        css = Path(settings.BASE_DIR, "static", "css", "erp.css").read_text(encoding="utf-8")
        self.assertIn(".min-w-0 { min-width: 0; }", css)
