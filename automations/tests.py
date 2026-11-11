from datetime import time, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from core.models import StudioSettings
from core.permissions import CLIENT, OWNER, TEAM
from crm.models import Lead

from . import engine
from .models import Automation, AutomationLog, MessageTemplate


def user(name, group):
    u = User.objects.create_user(username=name, password="pw12345!", first_name=name.title())
    u.groups.add(Group.objects.get_or_create(name=group)[0])
    return u


class RenderTests(TestCase):
    def test_only_known_placeholders_are_filled(self):
        out = engine.render("Hi {name}, {unknown} {name.__class__} {0} {{literal}}", {"name": "Asha"})
        self.assertEqual(out, "Hi Asha, {unknown} {name.__class__} {0} {literal}")

    def test_malformed_template_never_blocks_a_lead(self):
        engine.ensure_templates()
        MessageTemplate.objects.filter(key=Automation.NEW_LEAD).update(body="Lead {name} {")
        Lead.objects.create(name="Asha", mobile="9876500001")
        self.assertEqual(AutomationLog.objects.get(automation=Automation.NEW_LEAD).message, "Lead {name} {")
        self.assertIsNotNone(engine.check("Hi {name"))
        self.assertIsNotNone(engine.check("Hi {0}"))
        self.assertIsNone(engine.check("Hi {name}, see {link}"))


class TriggerTests(TestCase):
    def test_new_lead_alerts_owner(self):
        lead = Lead.objects.create(name="Ravi Kumar", mobile="9876543210", message="Need a modular kitchen")
        log = AutomationLog.objects.get(automation=Automation.NEW_LEAD)
        self.assertTrue(log.to_owner)
        self.assertEqual(log.lead, lead)
        self.assertIn("Ravi Kumar", log.message)
        self.assertIn("modular kitchen", log.message)

    def test_booking_confirmation(self):
        b = Booking.objects.create(name="Meera", mobile="9812345678", date=timezone.localdate() + timedelta(days=3),
                                   start_time=time(11, 0))
        log = AutomationLog.objects.get(automation=Automation.BOOKING_CONFIRMATION)
        self.assertEqual(log.booking, b)
        self.assertIn(b.reference, log.message)
        self.assertIn("11:00 AM", log.message)
        self.assertIn("wa.me/919812345678", engine.whatsapp_url(log))

    def test_switched_off_automation_logs_nothing(self):
        engine.ensure_templates()
        MessageTemplate.objects.filter(key=Automation.NEW_LEAD).update(is_active=False)
        Lead.objects.create(name="X", mobile="9876500000")
        self.assertFalse(AutomationLog.objects.filter(automation=Automation.NEW_LEAD).exists())

    def test_edited_template_is_used(self):
        engine.ensure_templates()
        MessageTemplate.objects.filter(key=Automation.NEW_LEAD).update(body="NEW: {name} / {mobile}")
        Lead.objects.create(name="Tara", mobile="9000000001")
        self.assertEqual(AutomationLog.objects.get(automation=Automation.NEW_LEAD).message, "NEW: Tara / 9000000001")


class ScheduledTests(TestCase):
    def test_reminder_once_per_booking(self):
        Booking.objects.create(name="Kiran", mobile="9812345670", date=timezone.localdate() + timedelta(days=1),
                               start_time=time(15, 0))
        first = engine.run_scheduled()
        self.assertEqual([m.automation for m in first].count(Automation.CONSULTATION_REMINDER), 1)
        second = engine.run_scheduled()
        self.assertEqual([m.automation for m in second].count(Automation.CONSULTATION_REMINDER), 0)

    def test_untouched_lead_followup(self):
        lead = Lead.objects.create(name="Old Lead", mobile="9000000002")
        Lead.objects.filter(pk=lead.pk).update(updated_at=timezone.now() - timedelta(days=5))
        made = engine.run_scheduled()
        follow = [m for m in made if m.automation == Automation.LEAD_FOLLOWUP]
        self.assertEqual(len(follow), 1)
        self.assertIn("5 days", follow[0].message)
        self.assertEqual(len([m for m in engine.run_scheduled() if m.automation == Automation.LEAD_FOLLOWUP]), 0)


class PageTests(TestCase):
    def setUp(self):
        self.owner = user("own", OWNER)
        self.team = user("tm", TEAM)
        self.client_user = user("cl", CLIENT)

    def test_access(self):
        url = reverse("automations:index")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.team)
        r = self.client.get(url)
        self.assertContains(r, "Working in the demo")
        self.assertNotContains(r, "Edit message")
        self.assertEqual(self.client.post(reverse("automations:toggle", args=["new_lead"])).status_code, 403)

    def test_owner_edits_toggles_and_runs(self):
        self.client.force_login(self.owner)
        self.client.get(reverse("automations:index"))
        key = Automation.QUOTATION_SENT
        self.client.post(reverse("automations:save", args=[key]), {"body": "Hello {name}", "action": "save"})
        self.assertEqual(MessageTemplate.objects.get(key=key).body, "Hello {name}")
        self.client.post(reverse("automations:save", args=[key]), {"body": "", "action": "save"})
        self.assertEqual(MessageTemplate.objects.get(key=key).body, "Hello {name}")
        self.client.post(reverse("automations:save", args=[key]), {"action": "reset"})
        self.assertEqual(MessageTemplate.objects.get(key=key).body, engine.DEFAULT_TEMPLATES[key])
        self.client.post(reverse("automations:toggle", args=[key]))
        self.assertFalse(MessageTemplate.objects.get(key=key).is_active)
        r = self.client.post(reverse("automations:run"), follow=True)
        self.assertEqual(r.status_code, 200)

    def test_log_shows_whatsapp_link_and_live_feed(self):
        Lead.objects.create(name="Feed Lead", mobile="9000000003")
        self.client.force_login(self.owner)
        r = self.client.get(reverse("automations:index"))
        self.assertContains(r, "Send via WhatsApp")
        since = (timezone.now() - timedelta(seconds=30)).isoformat()
        data = self.client.get(reverse("studio:client_activity"), {"since": since}).json()
        self.assertTrue(any(e["kind"] == "automation" for e in data["events"]))

    def test_module_off(self):
        s = StudioSettings.load()
        s.module_automation = False
        s.save()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("automations:index")).status_code, 404)
        r = self.client.get(reverse("studio:dashboard"))
        self.assertNotContains(r, 'href="%s"' % reverse("automations:index"))
        self.assertNotIn(reverse("automations:index"), [s["url"] for s in r.context["tour_steps"]])


class QuotationHookTests(TestCase):
    def test_sending_quotation_prepares_message(self):
        from crm.services import convert_lead
        from finance import services
        owner = user("own", OWNER)
        lead = Lead.objects.create(name="Neha Sharma", mobile="9876543210")
        project, _, _ = convert_lead(lead, owner)
        q = services.create_quotation(project=project, user=owner)
        services.save_builder(q, {"title": "T", "rooms": [{"name": "Kitchen", "items": [
            {"description": "Unit", "quantity": "1", "rate": "1000", "gst_percent": "18", "discount_percent": "0", "unit": "nos"}]}]})
        q.refresh_from_db()
        services.send_quotation(q)
        log = AutomationLog.objects.get(automation=Automation.QUOTATION_SENT)
        self.assertEqual(log.quotation, q)
        self.assertIn("₹1,180", log.message)


class TeamPageTests(TestCase):
    def setUp(self):
        self.owner = user("own", OWNER)
        self.team = user("tm", TEAM)

    def test_owner_only(self):
        self.client.force_login(self.team)
        self.assertEqual(self.client.get(reverse("studio:team")).status_code, 403)

    def test_add_and_deactivate_member(self):
        self.client.force_login(self.owner)
        r = self.client.post(reverse("studio:team"), {"action": "add", "first_name": "Sana", "username": "sana",
                                                      "role": TEAM, "password": "Interior#2026x"})
        self.assertEqual(r.status_code, 302)
        sana = User.objects.get(username="sana")
        self.assertTrue(sana.groups.filter(name=TEAM).exists())
        r = self.client.post(reverse("studio:team"), {"action": "add", "first_name": "Dup", "username": "SANA",
                                                      "role": TEAM, "password": "Interior#2026x"})
        self.assertContains(r, "already taken")
        self.client.post(reverse("studio:team"), {"action": "toggle", "user": sana.pk})
        sana.refresh_from_db()
        self.assertFalse(sana.is_active)
        self.client.post(reverse("studio:team"), {"action": "toggle", "user": self.owner.pk})
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_active)


class WhyAndTourTests(TestCase):
    @override_settings(DEMO_MODE=True)
    def test_why_page_has_packages_without_prices(self):
        from core.seed_sales import seed_packages
        from io import StringIO
        seed_packages(StringIO())
        r = self.client.get(reverse("website:why"))
        self.assertContains(r, "Complete System")
        self.assertContains(r, "Talk to us")
        self.assertContains(r, "illustration based only on your inputs")
        self.assertContains(r, 'id="tourSteps"')
        self.assertNotContains(r, "₹" + "0")

    @override_settings(DEMO_MODE=False)
    def test_why_hidden_outside_demo(self):
        self.assertEqual(self.client.get(reverse("website:why")).status_code, 404)
        self.assertNotContains(self.client.get("/"), 'id="tourSteps"')

    @override_settings(DEMO_MODE=True, LANDING_PAGE=True)
    def test_role_switch_honours_safe_next_only(self):
        user("owner", OWNER)
        r = self.client.post(reverse("core:switch_role", args=["owner"]), {"next": "/studio/leads/", "quiet": "1"})
        self.assertRedirects(r, "/studio/leads/", fetch_redirect_response=False)
        r = self.client.post(reverse("core:switch_role", args=["visitor"]), {"next": "https://evil.example/"})
        self.assertRedirects(r, reverse("website:home"), fetch_redirect_response=False)
