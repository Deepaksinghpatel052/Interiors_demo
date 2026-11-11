import io
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from core.permissions import CLIENT, OWNER, TEAM
from crm.models import Lead
from crm.services import convert_lead
from finance import services as fin
from studio.models import (ClientRequest, DesignProposal, Milestone, ProjectDocument, ProposalComment, ProposalImage,
                           Task)


def png():
    buf = io.BytesIO()
    Image.new("RGB", (30, 20), (0, 129, 246)).save(buf, "PNG")
    return buf.getvalue()


def make_user(name, group):
    u = User.objects.create_user(username=name, password="pw12345!", first_name=name.title())
    u.groups.add(Group.objects.get_or_create(name=group)[0])
    return u


class PortalBase(TestCase):
    def setUp(self):
        self.owner = make_user("own", OWNER)
        self.team = make_user("tm", TEAM)
        self.project, self.username, _ = convert_lead(
            Lead.objects.create(name="Rahul Verma", mobile="9827098270", property_type="3bhk"), self.owner)
        self.client_a = User.objects.get(username=self.username)
        self.other_project, other_username, _ = convert_lead(
            Lead.objects.create(name="Other Client", mobile="9827000001"), self.owner)
        self.client_b = User.objects.get(username=other_username)
        self.proposal = DesignProposal.objects.create(project=self.project, version=1, title="Concept",
                                                      status=DesignProposal.Status.SHARED, shared_at=timezone.now())
        self.image = ProposalImage(proposal=self.proposal, order=0)
        self.image.image.save("a.png", ContentFile(png()), save=True)
        self.client.force_login(self.client_a)

    def action(self, proposal, **data):
        return self.client.post(reverse("portal:design_action", args=[proposal.pk]), data)


class AccessTests(PortalBase):
    def test_client_sees_own_pages(self):
        for name in ["overview", "designs", "timeline", "updates", "documents", "payments", "requests"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"portal:{name}")).status_code, 200)
        self.assertContains(self.client.get(reverse("portal:overview")), "Rahul")

    def test_other_client_cannot_see_project_or_design(self):
        self.client.force_login(self.client_b)
        r = self.client.get(reverse("portal:overview"))
        self.assertNotContains(r, self.project.name)
        self.assertEqual(self.client.get(reverse("portal:design_detail", args=[self.proposal.pk])).status_code, 404)
        self.assertEqual(self.action(self.proposal, action="approve").status_code, 404)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, DesignProposal.Status.SHARED)
        # ?p= cannot switch to someone else's project
        r = self.client.get(reverse("portal:overview") + f"?p={self.project.pk}")
        self.assertNotContains(r, self.project.name)

    def test_documents_and_pdfs_are_private(self):
        doc = ProjectDocument(project=self.project, title="Agreement", kind="agreement", visible_to_client=True)
        doc.file.save("agreement.pdf", ContentFile(b"%PDF-1.4 test"), save=True)
        hidden = ProjectDocument(project=self.project, title="Internal costing", kind="other", visible_to_client=False)
        hidden.file.save("costing.pdf", ContentFile(b"%PDF-1.4 secret"), save=True)
        q = fin.create_quotation(project=self.project)
        fin.save_builder(q, {"rooms": [{"name": "Room", "items": [{"description": "Work", "quantity": "1", "rate": "10000"}]}]})
        draft = fin.create_quotation(project=self.project)
        fin.send_quotation(q)
        inv = fin.raise_invoice(fin.accept_quotation(q, self.owner)[0])

        self.assertEqual(self.client.get(reverse("portal:document_download", args=[doc.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("portal:document_download", args=[hidden.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("portal:quotation_pdf", args=[draft.pk])).status_code, 404)
        self.assertTrue(self.client.get(reverse("portal:quotation_pdf", args=[q.pk])).content.startswith(b"%PDF"))
        self.assertTrue(self.client.get(reverse("portal:invoice_pdf", args=[inv.pk])).content.startswith(b"%PDF"))
        self.client.force_login(self.client_b)
        for url in [reverse("portal:document_download", args=[doc.pk]), reverse("portal:quotation_pdf", args=[q.pk]),
                    reverse("portal:invoice_pdf", args=[inv.pk])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_non_clients_kept_out(self):
        self.client.force_login(self.team)
        self.assertEqual(self.client.get(reverse("portal:overview")).status_code, 403)
        self.client.logout()
        r = self.client.get(reverse("portal:overview"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("core:login"), r.url)

    def test_client_cannot_open_studio(self):
        self.assertEqual(self.client.get(reverse("studio:dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("studio:client_activity")).status_code, 403)

    def test_client_login_lands_in_portal(self):
        self.client.logout()
        self.client_a.set_password("pw12345!")
        self.client_a.save()
        r = self.client.post(reverse("core:login"), {"username": self.username, "password": "pw12345!"}, follow=True)
        self.assertEqual(r.redirect_chain[-1][0], reverse("portal:overview"))


class DesignActionTests(PortalBase):
    def test_approve_moves_project_forward(self):
        self.action(self.proposal, action="approve", text="Looks perfect!")
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, DesignProposal.Status.APPROVED)
        self.assertEqual(self.proposal.decision_comment, "Looks perfect!")
        approval = self.project.milestones.get(title__icontains="approval")
        self.assertEqual(approval.status, Milestone.Status.DONE)
        self.assertEqual(self.project.milestones.get(title="Material ordering").status, Milestone.Status.IN_PROGRESS)
        # cannot approve twice
        self.action(self.proposal, action="changes", text="Actually change the colour")
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, DesignProposal.Status.APPROVED)

    def test_request_changes_needs_comment_and_creates_task(self):
        self.action(self.proposal, action="changes", text="no")
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, DesignProposal.Status.SHARED)
        self.action(self.proposal, action="changes", text="Please make the TV wall lighter")
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, DesignProposal.Status.CHANGES)
        task = Task.objects.get(from_client=True)
        self.assertEqual((task.priority, task.project), (Task.Priority.HIGH, self.project))

    def test_cannot_approve_older_version(self):
        DesignProposal.objects.create(project=self.project, version=2, title="Revised",
                                      status=DesignProposal.Status.SHARED, shared_at=timezone.now())
        self.action(self.proposal, action="approve")
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, DesignProposal.Status.SHARED)

    def test_comment_on_image(self):
        self.action(self.proposal, action="comment", text="Can this be lighter?", image=self.image.pk)
        c = ProposalComment.objects.get()
        self.assertEqual((c.image, c.author), (self.image, self.client_a))
        foreign = DesignProposal.objects.create(project=self.other_project, version=1, title="X",
                                                status=DesignProposal.Status.SHARED)
        other_img = ProposalImage(proposal=foreign, order=0)
        other_img.image.save("b.png", ContentFile(png()), save=True)
        self.action(self.proposal, action="comment", text="sneaky", image=other_img.pk)
        self.assertEqual(ProposalComment.objects.count(), 1)

    def test_comment_is_escaped(self):
        self.action(self.proposal, action="comment", text="<script>alert(1)</script>")
        r = self.client.get(reverse("portal:design_detail", args=[self.proposal.pk]))
        self.assertNotContains(r, "<script>alert(1)</script>")
        self.assertContains(r, "&lt;script&gt;")

    def test_drafts_hidden(self):
        draft = DesignProposal.objects.create(project=self.project, version=3, title="Draft", status=DesignProposal.Status.DRAFT)
        self.assertEqual(self.client.get(reverse("portal:design_detail", args=[draft.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("portal:designs")), "Draft")


class RequestAndLiveTests(PortalBase):
    def test_request_creates_task(self):
        r = self.client.post(reverse("portal:requests"), {
            "title": "Hinge loose", "description": "Kitchen top cabinet", "urgent": "on",
            "photo": SimpleUploadedFile("snag.png", png(), "image/png")})
        self.assertRedirects(r, reverse("portal:requests"))
        req = ClientRequest.objects.get()
        self.assertTrue(req.photo)
        self.assertEqual((req.task.priority, req.task.from_client, req.task.assigned_to),
                         (Task.Priority.HIGH, True, self.project.designer))

    def test_request_rejects_fake_photo(self):
        self.client.post(reverse("portal:requests"), {"title": "Hinge loose",
                                                      "photo": SimpleUploadedFile("x.png", b"<?php", "image/png")})
        self.assertFalse(ClientRequest.objects.exists())

    def test_studio_sees_client_activity(self):
        since = (timezone.now() - timedelta(seconds=5)).isoformat()
        self.action(self.proposal, action="approve")
        self.client.post(reverse("portal:requests"), {"title": "Paint touch-up"})
        self.client.force_login(self.owner)
        events = self.client.get(reverse("studio:client_activity"), {"since": since}).json()["events"]
        kinds = sorted(e["kind"] for e in events if e["kind"] != "automation")
        self.assertEqual(kinds, ["approved", "request"])
        self.assertIn("approved design v1", " ".join(e["text"] for e in events))
        dash = self.client.get(reverse("studio:dashboard"))
        self.assertContains(dash, "From your clients")
