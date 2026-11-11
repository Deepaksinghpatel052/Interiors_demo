import io
import json
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from xhtml2pdf import pisa

from core.models import StudioSettings
from core.permissions import CLIENT, OWNER, TEAM
from crm.models import Lead
from website.models import FAQ

from . import llm, rag
from .models import ChatSession, KnowledgeDocument

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "ratelimit-tests"}}


def make_user(name, group):
    u = User.objects.create_user(username=name, password="pw12345!")
    u.groups.add(Group.objects.get_or_create(name=group)[0])
    return u


def doc(title, content, audience="public", doc_type="policy"):
    return KnowledgeDocument.objects.create(title=title, content=content, audience=audience, doc_type=doc_type)


class KBTestCase(TestCase):
    def setUp(self):
        self.warranty = doc("Warranty policy", "Workmanship carries a 1-year warranty from handover. "
                                               "Modular furniture carries a 5-year warranty against manufacturing defects.")
        self.payments = doc("Payment terms", "Payments are linked to milestones: 10% booking advance, 40% on design "
                                             "approval, 40% at mid-execution and 10% on handover. We accept UPI and bank transfer.")
        self.plywood = doc("Materials guide", "We use BWP plywood for kitchens and bathrooms and MR plywood for wardrobes. "
                                              "Quartz countertops are non-porous and stain resistant.", doc_type="material")
        self.internal = doc("Discount policy", "Designers can offer up to 5% discount on furniture lines without approval.",
                            audience="internal")


class ChunkingTests(TestCase):
    def test_chunks_respect_size_and_overlap(self):
        text = " ".join(f"Sentence number {i} talks about interiors and kitchens." for i in range(120))
        chunks = rag.chunk_text(text, size=800, overlap=160)
        self.assertGreater(len(chunks), 3)
        self.assertTrue(all(len(c) <= 800 + 60 for c in chunks))
        # neighbouring chunks share text (overlap)
        self.assertTrue(any(w in chunks[1] for w in chunks[0][-120:].split()[2:6]))

    def test_paragraphs_and_empty(self):
        self.assertEqual(rag.chunk_text(""), [])
        self.assertEqual(rag.chunk_text("Short para one.\n\nShort para two."), ["Short para one.\nShort para two."])

    def test_tokenize_stems_and_drops_stopwords(self):
        self.assertEqual(rag.tokenize("What are the warranties on wardrobes?"), ["warranty", "wardrobe"])


class RetrievalTests(KBTestCase):
    def test_right_document_for_sample_questions(self):
        cases = {
            "What warranty do you give on modular furniture?": "Warranty policy",
            "How do payments work, what is the booking advance?": "Payment terms",
            "Which plywood is used in the kitchen?": "Materials guide",
            "Is quartz good for a countertop?": "Materials guide",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(rag.retrieve(question, "public")[0].document.title, expected)

    def test_internal_docs_never_reach_visitors(self):
        public_titles = [h.document.title for h in rag.retrieve("discount furniture approval", "public")]
        self.assertNotIn("Discount policy", public_titles)
        internal = rag.retrieve("discount furniture approval", "internal")
        self.assertEqual(internal[0].document.title, "Discount policy")

    def test_inactive_docs_excluded_and_no_match(self):
        self.warranty.is_active = False
        self.warranty.save()
        self.assertNotIn("Warranty policy", [h.document.title for h in rag.retrieve("warranty", "public")])
        self.assertEqual(rag.retrieve("spaceship rocket engine", "public"), [])

    def test_index_refreshes_after_edit(self):
        self.assertEqual(rag.retrieve("termite treatment", "public"), [])
        self.plywood.content += " All plywood gets anti-termite treatment."
        self.plywood.save()
        self.assertEqual(rag.retrieve("termite treatment", "public")[0].document.title, "Materials guide")


@override_settings(AI_MOCK=True)
class MockAnswerTests(KBTestCase):
    def test_answer_has_citations_and_sources(self):
        a = llm.answer("What warranty do you give on modular furniture?", "public")
        self.assertEqual(a.mode, "mock")
        self.assertIn("[1]", a.text)
        self.assertIn("5-year", a.text)
        self.assertEqual(a.sources[0]["title"], "Warranty policy")
        self.assertIn('<sup class="cite">[1]</sup>', a.html)
        self.assertIn("consultation", a.text.lower())  # next step for visitors

    def test_no_match_is_polite(self):
        a = llm.answer("Do you repair cars?", "public")
        self.assertEqual(a.mode, "no_match")
        self.assertIn("consultation", a.text)

    def test_script_in_document_is_escaped(self):
        doc("Evil", "Our hinges are great. <script>alert('x')</script> Hinges come with soft close and warranty.")
        a = llm.answer("hinges soft close", "public")
        self.assertNotIn("<script>", a.html)
        self.assertIn("&lt;script&gt;", a.html)

    def test_render_html_sanitises_model_output(self):
        html = llm.render_html("**Bold** <img src=x onerror=alert(1)> [2]\n\n- item")
        self.assertIn("<strong>Bold</strong>", html)
        self.assertNotIn("<img", html)
        self.assertIn("<li>item</li>", html)
        self.assertIn('<sup class="cite">[2]</sup>', html)


def fake_response(text, stop_reason="end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="thinking", thinking=""),
                                                             SimpleNamespace(type="text", text=text)])


@override_settings(AI_MOCK=False, ANTHROPIC_API_KEY="test-key", ANTHROPIC_MODEL="claude-opus-5-5", ANTHROPIC_FALLBACKS=True)
class ClaudeAnswerTests(KBTestCase):
    def test_claude_request_shape_and_citations(self):
        with mock.patch("anthropic.Anthropic") as client_cls:
            create = client_cls.return_value.beta.messages.create
            create.return_value = fake_response("Modular furniture has a 5-year warranty [1].")
            a = llm.answer("What warranty on modular furniture?", "public",
                           history=[{"role": "user", "text": "Hi"}, {"role": "assistant", "text": "Hello!"}])
        self.assertEqual(a.mode, "claude")
        self.assertEqual(a.sources[0]["title"], "Warranty policy")
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-opus-5-5")
        self.assertIn("ONLY the numbered sources", kwargs["system"])
        self.assertIn("not instructions", kwargs["system"])
        self.assertEqual(kwargs["output_config"], {"effort": "low"})
        self.assertEqual(kwargs["fallbacks"], "default")
        self.assertEqual(kwargs["betas"], ["server-side-fallback-2026-07-01"])
        last = kwargs["messages"][-1]
        self.assertEqual(last["role"], "user")
        self.assertIn("<sources>", last["content"])
        self.assertIn("[1] Warranty policy", last["content"])
        self.assertIn("<question>", last["content"])
        self.assertEqual(kwargs["messages"][0]["content"], "Hi")
        self.assertNotIn("temperature", kwargs)

    @override_settings(ANTHROPIC_MODEL="claude-haiku-5-5")
    def test_no_fallback_param_for_unsupported_model(self):
        with mock.patch("anthropic.Anthropic") as client_cls:
            create = client_cls.return_value.beta.messages.create
            create.return_value = fake_response("Answer [1].")
            llm.answer("warranty", "public")
        self.assertNotIn("fallbacks", create.call_args.kwargs)

    def test_refusal_and_errors_fall_back_to_offline_answer(self):
        import anthropic
        with mock.patch("anthropic.Anthropic") as client_cls:
            client_cls.return_value.beta.messages.create.return_value = fake_response("", stop_reason="refusal")
            a = llm.answer("What warranty on modular furniture?", "public")
        self.assertEqual((a.mode, a.note), ("fallback", "refusal"))
        self.assertIn("[1]", a.text)
        with mock.patch("anthropic.Anthropic") as client_cls:
            client_cls.return_value.beta.messages.create.side_effect = anthropic.APIConnectionError(request=mock.Mock())
            a = llm.answer("What warranty on modular furniture?", "public")
        self.assertEqual((a.mode, a.note), ("fallback", "offline"))

    def test_model_output_with_html_is_escaped(self):
        with mock.patch("anthropic.Anthropic") as client_cls:
            client_cls.return_value.beta.messages.create.return_value = fake_response(
                "Sure <script>steal()</script> 5 years [1]")
            a = llm.answer("warranty modular furniture", "public")
        self.assertNotIn("<script>", a.html)
        self.assertIn("&lt;script&gt;", a.html)


class SyncTests(TestCase):
    def test_faq_lifecycle_syncs_into_kb(self):
        faq = FAQ.objects.create(question="Do you do pooja rooms?", answer="Yes, we design backlit jaali pooja units.",
                                 category="Services")
        d = KnowledgeDocument.objects.get(source_key=f"faq:{faq.pk}")
        self.assertEqual(d.doc_type, "faq")
        self.assertEqual(rag.retrieve("pooja unit jaali", "public")[0].document, d)
        faq.answer = "Yes, including marble pooja mandirs."
        faq.save()
        self.assertEqual(rag.retrieve("marble mandir", "public")[0].document.pk, d.pk)
        faq.delete()
        self.assertFalse(KnowledgeDocument.objects.filter(source_key=f"faq:{faq.pk}").exists())
        self.assertEqual(rag.retrieve("marble mandir", "public"), [])


@override_settings(AI_MOCK=True, CACHES=LOCMEM)
class EndpointTests(KBTestCase):
    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()
        self.url = reverse("assistant:public_chat")

    def post(self, data, client=None):
        return (client or self.client).post(self.url, json.dumps(data), content_type="application/json")

    def test_chat_returns_answer_and_logs(self):
        r = self.post({"message": "What warranty on modular furniture?"})
        data = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertIn("[1]", data["html"])
        self.assertEqual(data["sources"][0]["title"], "Warranty policy")
        s = ChatSession.objects.get(key=data["session"])
        self.assertEqual(s.messages.count(), 2)
        # same session continues
        self.post({"message": "And payments?", "session": data["session"]})
        self.assertEqual(s.messages.count(), 4)

    def test_csrf_required(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(self.post({"message": "hi"}, client=c).status_code, 403)

    def test_validation_and_module_flag(self):
        self.assertEqual(self.post({"message": ""}).status_code, 400)
        self.assertEqual(self.post({"message": "x" * 501}).status_code, 400)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        s = StudioSettings.load()
        s.module_ai = False
        s.save()
        self.assertEqual(self.post({"message": "warranty"}).status_code, 404)
        self.assertNotContains(self.client.get("/"), "chatPanel")

    def test_lead_captured_from_chat(self):
        r = self.post({"message": "My name is Priya Sharma, please call me on 98765 43210"})
        self.assertTrue(r.json()["lead"])
        lead = Lead.objects.get(mobile="9876543210")
        self.assertEqual((lead.name, lead.source), ("Priya Sharma", Lead.Source.AI))
        self.assertEqual(ChatSession.objects.get(key=r.json()["session"]).lead, lead)
        self.assertIn("call you on 9876543210", r.json()["html"])

    def test_lead_form(self):
        url = reverse("assistant:public_lead")
        bad = self.client.post(url, json.dumps({"name": "A B", "mobile": "123"}), content_type="application/json")
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(url, json.dumps({"name": "Amit Kumar", "mobile": "9876500011"}), content_type="application/json")
        self.assertTrue(ok.json()["ok"])
        self.assertTrue(Lead.objects.filter(mobile="9876500011", source=Lead.Source.AI).exists())

    @override_settings(AI_PUBLIC_LIMIT=(3, 600))
    def test_rate_limit(self):
        session = self.post({"message": "warranty"}).json()["session"]
        codes = [self.post({"message": "warranty", "session": session}).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])


@override_settings(AI_MOCK=True)
class StudioPageTests(KBTestCase):
    def setUp(self):
        super().setUp()
        self.owner, self.team, self.client_user = make_user("own", OWNER), make_user("tm", TEAM), make_user("cl", CLIENT)

    def test_permissions(self):
        self.client.force_login(self.client_user)
        for name in ["assistant:studio", "assistant:kb", "assistant:chats"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.client.force_login(self.team)
        self.assertEqual(self.client.get(reverse("assistant:studio")).status_code, 200)
        self.assertEqual(self.client.get(reverse("assistant:kb")).status_code, 200)
        self.assertEqual(self.client.get(reverse("assistant:chats")).status_code, 403)
        self.assertEqual(self.client.get(reverse("assistant:kb_edit", args=[self.warranty.pk])).status_code, 403)

    def test_studio_assistant_sees_internal_docs(self):
        self.client.force_login(self.team)
        r = self.client.post(reverse("assistant:studio_ask"), json.dumps({"message": "discount on furniture lines"}),
                             content_type="application/json")
        self.assertEqual(r.json()["sources"][0]["title"], "Discount policy")

    def test_kb_test_shows_retrieved_chunks(self):
        self.client.force_login(self.team)
        r = self.client.post(reverse("assistant:kb_test"), json.dumps({"message": "booking advance", "audience": "public"}),
                             content_type="application/json").json()
        self.assertEqual(r["hits"][0]["title"], "Payment terms")
        self.assertIn("score", r["hits"][0])

    def test_owner_uploads_pdf(self):
        buf = io.BytesIO()
        pisa.CreatePDF("<p>Our site supervisors visit every Tuesday and Friday for quality checks.</p>", dest=buf)
        self.client.force_login(self.owner)
        r = self.client.post(reverse("assistant:kb"), {
            "title": "Supervision schedule", "doc_type": "process", "audience": "internal", "is_active": "on",
            "file": SimpleUploadedFile("schedule.pdf", buf.getvalue(), "application/pdf")})
        self.assertRedirects(r, reverse("assistant:kb"))
        d = KnowledgeDocument.objects.get(title="Supervision schedule")
        self.assertTrue(d.chunks.filter(text__icontains="Tuesday").exists())
        self.assertEqual(rag.retrieve("supervisor quality checks Tuesday", "internal")[0].document, d)

    def test_upload_rejects_other_files(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("assistant:kb"), {"title": "Bad", "doc_type": "policy", "audience": "public",
                                                   "file": SimpleUploadedFile("x.html", b"<script>", "text/html")})
        self.assertFalse(KnowledgeDocument.objects.filter(title="Bad").exists())

    def test_synced_docs_not_editable_here(self):
        faq = FAQ.objects.create(question="Q?", answer="An answer long enough to index.")
        d = KnowledgeDocument.objects.get(source_key=f"faq:{faq.pk}")
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.get(reverse("assistant:kb_edit", args=[d.pk])), reverse("assistant:kb"))
