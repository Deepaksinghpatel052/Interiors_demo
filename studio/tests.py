import io
import json
from datetime import time, timedelta

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from bookings.models import Booking
from core.permissions import CLIENT, OWNER, TEAM
from crm.models import Lead
from crm.services import convert_lead

from .models import ClientProject, DesignProposal, Milestone, ProjectDocument, Task


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (180, 120, 90)).save(buf, "PNG")
    return buf.getvalue()


def make_user(username, group, **kw):
    u = User.objects.create_user(username=username, password="pw12345!", first_name=username.title(), **kw)
    u.groups.add(Group.objects.get_or_create(name=group)[0])
    return u


class ErpTestCase(TestCase):
    def setUp(self):
        self.owner = make_user("own", OWNER)
        self.team = make_user("tm", TEAM)
        self.client_user = make_user("cl", CLIENT)
        self.lead = Lead.objects.create(name="Neha Sharma", mobile="9876543210", property_type="2bhk")

    def login(self, user):
        self.client.force_login(user)


class PermissionTests(ErpTestCase):
    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("studio:dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("core:login"), r.url)

    def test_client_cannot_open_erp(self):
        self.login(self.client_user)
        for name in ["dashboard", "leads", "bookings", "projects", "tasks"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"studio:{name}")).status_code, 403)
        self.assertEqual(self.client.get(reverse("studio:lead_detail", args=[self.lead.pk])).status_code, 403)

    def test_team_member_pages(self):
        self.login(self.team)
        for name in ["dashboard", "leads", "bookings", "projects", "tasks", "lead_create"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"studio:{name}")).status_code, 200)
        # owner-only areas
        self.assertEqual(self.client.get(reverse("studio:availability")).status_code, 403)
        self.assertEqual(self.client.get(reverse("studio:project_create")).status_code, 403)
        self.assertEqual(self.client.post(reverse("studio:lead_convert", args=[self.lead.pk])).status_code, 403)

    def test_owner_pages(self):
        self.login(self.owner)
        for name in ["dashboard", "availability", "project_create"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"studio:{name}")).status_code, 200)

    def test_login_redirects_by_role(self):
        r = self.client.post(reverse("core:login"), {"username": "tm", "password": "pw12345!"}, follow=True)
        self.assertEqual(r.redirect_chain[-1][0], reverse("studio:dashboard"))


class LeadTests(ErpTestCase):
    def test_kanban_move(self):
        self.login(self.team)
        r = self.client.post(reverse("studio:lead_move"), json.dumps(
            {"lead": self.lead.pk, "stage": "consultation", "order": [self.lead.pk]}), content_type="application/json")
        self.assertEqual(r.json()["stage_label"], "Consultation")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.stage, "consultation")
        self.assertTrue(self.lead.activities.filter(text__contains="Consultation").exists())

    def test_kanban_rejects_bad_stage(self):
        self.login(self.team)
        r = self.client.post(reverse("studio:lead_move"), json.dumps({"lead": self.lead.pk, "stage": "hacked"}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_convert_lead_creates_client_project(self):
        project, username, password = convert_lead(self.lead, self.owner)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.stage, "won")
        self.assertEqual(project.lead, self.lead)
        self.assertEqual(project.milestones.count(), 5)
        self.assertTrue(project.code.startswith("PRJ-"))
        user = User.objects.get(username=username)
        self.assertTrue(user.groups.filter(name=CLIENT).exists())
        self.assertTrue(user.check_password(password))
        # idempotent
        again, u2, p2 = convert_lead(self.lead, self.owner)
        self.assertEqual(again.pk, project.pk)
        self.assertIsNone(u2)
        self.assertEqual(ClientProject.objects.count(), 1)

    def test_convert_via_view(self):
        self.login(self.owner)
        r = self.client.post(reverse("studio:lead_convert", args=[self.lead.pk]))
        project = ClientProject.objects.get()
        self.assertRedirects(r, project.get_absolute_url())

    def test_lead_create_and_note(self):
        self.login(self.team)
        r = self.client.post(reverse("studio:lead_create"), {
            "name": "Walk In", "mobile": "98765 00000", "source": "walk_in", "stage": "new"})
        lead = Lead.objects.get(name="Walk In")
        self.assertRedirects(r, reverse("studio:lead_detail", args=[lead.pk]))
        self.client.post(reverse("studio:lead_note", args=[lead.pk]), {"text": "Called, visiting Sunday"})
        self.assertTrue(lead.activities.filter(text="Called, visiting Sunday").exists())

    def test_lead_text_is_escaped(self):
        self.lead.notes = "<script>alert(1)</script>"
        self.lead.save()
        self.login(self.team)
        r = self.client.get(reverse("studio:lead_detail", args=[self.lead.pk]))
        self.assertNotContains(r, "<script>alert(1)</script>")


class BookingCalendarTests(ErpTestCase):
    def setUp(self):
        super().setUp()
        self.day = timezone.localdate() + timedelta(days=3)
        self.b1 = Booking.objects.create(date=self.day, start_time=time(10), name="A", mobile="9876543210", lead=self.lead)
        self.b2 = Booking.objects.create(date=self.day, start_time=time(12), name="B", mobile="9876543211")
        self.login(self.team)

    def test_events_feed(self):
        r = self.client.get(reverse("studio:booking_events"), {"start": str(self.day), "end": str(self.day + timedelta(days=1))})
        titles = [e["title"] for e in r.json()]
        self.assertEqual(len(titles), 2)

    def _move(self, booking, hhmm):
        return self.client.post(reverse("studio:booking_move", args=[booking.pk]),
                                json.dumps({"start": f"{self.day}T{hhmm}:00+05:30"}), content_type="application/json")

    def test_reschedule(self):
        r = self._move(self.b1, "11:00")
        self.assertTrue(r.json()["ok"])
        self.b1.refresh_from_db()
        self.assertEqual(self.b1.start_time, time(11))
        self.assertTrue(self.lead.activities.filter(text__contains="Rescheduled").exists())

    def test_reschedule_refuses_clash(self):
        r = self._move(self.b1, "12:00")
        self.assertEqual(r.status_code, 409)
        self.b1.refresh_from_db()
        self.assertEqual(self.b1.start_time, time(10))

    def test_status_change(self):
        self.client.post(reverse("studio:booking_status", args=[self.b2.pk]), {"status": "completed"})
        self.b2.refresh_from_db()
        self.assertEqual(self.b2.status, "completed")


class ProjectTests(ErpTestCase):
    def setUp(self):
        super().setUp()
        self.project, _, _ = convert_lead(self.lead, self.owner)
        self.login(self.team)

    def test_detail_tabs_render(self):
        for tab in ["overview", "tasks", "designs", "updates", "documents", "bogus"]:
            with self.subTest(tab=tab):
                self.assertEqual(self.client.get(self.project.get_absolute_url() + f"?tab={tab}").status_code, 200)

    def test_progress_from_milestones(self):
        self.assertEqual(self.project.progress, 0)
        m = self.project.milestones.first()
        self.client.post(reverse("studio:milestone_status", args=[m.pk]), {"status": "done"})
        self.assertEqual(ClientProject.objects.get(pk=self.project.pk).progress, 20)

    def test_task_lifecycle(self):
        self.client.post(reverse("studio:task_add", args=[self.project.pk]),
                         {"title": "Order laminates", "priority": "normal", "assigned_to": self.team.pk})
        task = Task.objects.get()
        self.client.post(reverse("studio:task_status", args=[task.pk]), {"status": "done"})
        task.refresh_from_db()
        self.assertEqual(task.status, "done")
        self.assertIsNotNone(task.completed_at)

    def test_project_kanban_move(self):
        r = self.client.post(reverse("studio:project_move"), json.dumps({"project": self.project.pk, "stage": "execution"}),
                             content_type="application/json")
        self.assertTrue(r.json()["ok"])

    def test_upload_design_version(self):
        r = self.client.post(reverse("studio:proposal_add", args=[self.project.pk]), {
            "title": "Concept", "notes": "", "share": "on",
            "images": [SimpleUploadedFile("a.png", png_bytes(), "image/png"),
                       SimpleUploadedFile("b.png", png_bytes(), "image/png")]})
        self.assertEqual(r.status_code, 302)
        p = DesignProposal.objects.get()
        self.assertEqual((p.version, p.status, p.images.count()), (1, "shared", 2))
        self.client.post(reverse("studio:proposal_add", args=[self.project.pk]), {
            "title": "Revised", "images": [SimpleUploadedFile("c.png", png_bytes(), "image/png")]})
        self.assertEqual(DesignProposal.objects.order_by("-version").first().version, 2)

    def test_upload_rejects_fake_image(self):
        self.client.post(reverse("studio:proposal_add", args=[self.project.pk]), {
            "title": "Bad", "images": [SimpleUploadedFile("evil.png", b"<?php echo 1; ?>", "image/png")]})
        self.assertFalse(DesignProposal.objects.exists())

    def test_upload_rejects_fake_pdf_and_bad_type(self):
        self.client.post(reverse("studio:document_add", args=[self.project.pk]), {
            "title": "Agreement", "kind": "agreement", "file": SimpleUploadedFile("a.pdf", b"not a pdf", "application/pdf")})
        self.client.post(reverse("studio:document_add", args=[self.project.pk]), {
            "title": "Script", "kind": "other", "file": SimpleUploadedFile("x.html", b"<script>", "text/html")})
        self.assertFalse(ProjectDocument.objects.exists())
        self.client.post(reverse("studio:document_add", args=[self.project.pk]), {
            "title": "Agreement", "kind": "agreement", "visible_to_client": "on",
            "file": SimpleUploadedFile("a.pdf", b"%PDF-1.4 minimal", "application/pdf")})
        self.assertEqual(ProjectDocument.objects.count(), 1)

    @override_settings(MAX_UPLOAD_MB=0)
    def test_upload_size_limit(self):
        self.client.post(reverse("studio:document_add", args=[self.project.pk]), {
            "title": "Big", "kind": "other", "file": SimpleUploadedFile("a.pdf", b"%PDF-1.4 big", "application/pdf")})
        self.assertFalse(ProjectDocument.objects.exists())

    def test_dashboard_counts(self):
        r = self.client.get(reverse("studio:dashboard"))
        self.assertEqual(r.context["kpis"]["active_projects"], 1)
        self.assertContains(r, "chartData")


@override_settings(DEMO_MODE=True)
class RoleSwitcherTests(TestCase):
    def setUp(self):
        make_user("owner", OWNER)

    def test_switch_to_owner_and_back(self):
        r = self.client.post(reverse("core:switch_role", args=["owner"]))
        self.assertRedirects(r, reverse("studio:dashboard"))
        r = self.client.post(reverse("core:switch_role", args=["visitor"]))
        self.assertRedirects(r, "/")   # LANDING_PAGE off: the studio home is /
        self.assertEqual(self.client.get(reverse("studio:dashboard")).status_code, 302)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("core:switch_role", args=["owner"])).status_code, 405)

    @override_settings(DEMO_MODE=False)
    def test_disabled_outside_demo(self):
        self.assertEqual(self.client.post(reverse("core:switch_role", args=["owner"])).status_code, 404)


class StudioSettingsPageTests(ErpTestCase):
    def valid_data(self, **overrides):
        from core.models import StudioSettings

        from .forms import StudioSettingsForm
        form = StudioSettingsForm(instance=StudioSettings.load())
        data = {}
        for name, field in form.fields.items():
            if name == "logo":
                continue
            value = form.initial.get(name, field.initial)
            if isinstance(field.widget, __import__("django").forms.CheckboxInput):
                if value:
                    data[name] = "on"
            else:
                data[name] = "" if value is None else value
        data.update(overrides)
        return data

    def test_owner_can_open_team_and_client_cannot(self):
        self.login(self.owner)
        self.assertEqual(self.client.get(reverse("studio:settings")).status_code, 200)
        self.login(self.team)
        self.assertEqual(self.client.get(reverse("studio:settings")).status_code, 403)
        self.login(self.client_user)
        self.assertEqual(self.client.get(reverse("studio:settings")).status_code, 403)

    def test_save_rebrands_site(self):
        from core.models import StudioSettings
        self.login(self.owner)
        r = self.client.post(reverse("studio:settings"), self.valid_data(
            name="Sharma Interiors", accent_color="#AA2233", schedule_text="Booking | 20\nDesign | 30\nHandover | 50"))
        self.assertRedirects(r, reverse("studio:settings"))
        s = StudioSettings.load()
        self.assertEqual((s.name, s.accent_color), ("Sharma Interiors", "#AA2233"))
        self.assertEqual(s.payment_schedule, [{"label": "Booking", "percent": 20}, {"label": "Design", "percent": 30},
                                              {"label": "Handover", "percent": 50}])
        self.assertContains(self.client.get("/"), "Sharma Interiors")

    def test_schedule_must_total_100(self):
        self.login(self.owner)
        r = self.client.post(reverse("studio:settings"), self.valid_data(schedule_text="Booking | 10\nRest | 50"))
        self.assertContains(r, "add up to 60%")

    def test_invalid_gstin_and_colour_rejected(self):
        self.login(self.owner)
        r = self.client.post(reverse("studio:settings"), self.valid_data(gstin="12345", accent_color="blue"))
        self.assertContains(r, "valid 15-character GSTIN")
        self.assertContains(r, "hex colour")

    def test_fake_logo_rejected(self):
        self.login(self.owner)
        data = self.valid_data()
        data["logo"] = SimpleUploadedFile("logo.png", b"<script>x</script>", "image/png")
        r = self.client.post(reverse("studio:settings"), data)
        self.assertEqual(r.status_code, 200)
        from core.models import StudioSettings
        self.assertFalse(StudioSettings.load().logo)
