from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import FeatureInterest, StudioSettings
from crm.models import Lead

from . import estimator, quiz
from .models import PortfolioProject, ProjectSwatch

TINY_JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


class EstimatorTests(TestCase):
    def setUp(self):
        self.s = StudioSettings.load()  # essential 1200, premium 1900, luxury 3000

    def test_range_uses_settings_rate(self):
        r = estimator.calculate("2bhk", ["living", "kitchen"], "premium", 1000, self.s)
        # 1000 × 1900 = 19,00,000 → 0.90× = 17,10,000 ; 1.15× = 21,85,000 → rounded to ₹10,000
        self.assertEqual((r["low"], r["high"]), (1710000, 2190000))
        self.assertEqual(r["rate"], 1900)

    def test_rates_are_editable(self):
        self.s.rate_luxury = 4000
        self.s.save()
        r = estimator.calculate("villa", ["living"], "luxury", 500, StudioSettings.load())
        self.assertEqual((r["low"], r["high"]), (1800000, 2300000))

    def test_finish_levels_ordered(self):
        lows = [estimator.calculate("3bhk", ["living"], f, 1200, self.s)["low"] for f in ("essential", "premium", "luxury")]
        self.assertEqual(lows, sorted(lows))
        self.assertLess(lows[0], lows[2])

    def test_invalid_inputs(self):
        for args in [("castle", ["living"], "premium", 900), ("2bhk", [], "premium", 900),
                     ("2bhk", ["living"], "gold", 900), ("2bhk", ["living"], "premium", 10),
                     ("2bhk", ["living"], "premium", "abc")]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                estimator.calculate(*args, self.s)

    def test_api_and_lead(self):
        r = self.client.get(reverse("website:api_estimate"),
                            {"property_type": "2bhk", "rooms": ["living", "kitchen"], "finish": "essential", "area": 800})
        self.assertEqual(r.json()["low"], 860000)
        self.assertEqual(self.client.get(reverse("website:api_estimate"), {"property_type": "x"}).status_code, 400)
        r = self.client.post(reverse("website:estimate"), {
            "property_type": "2bhk", "rooms": ["living", "kitchen"], "finish": "essential", "area": 800,
            "name": "Amit Kumar", "mobile": "9876543210"})
        self.assertRedirects(r, reverse("website:thanks"))
        lead = Lead.objects.get()
        self.assertEqual(lead.source, Lead.Source.ESTIMATOR)
        self.assertEqual(lead.estimate["high"], 1100000)
        self.assertIn("₹8,60,000", lead.message)


class QuizTests(TestCase):
    def test_score_majority(self):
        self.assertEqual(quiz.score(["modern", "luxury", "luxury", "minimal", "luxury"]), "luxury")

    def test_score_tie_goes_to_first_answer(self):
        self.assertEqual(quiz.score(["minimal", "modern", "modern", "minimal", "luxury"]), "minimal")

    def test_score_ignores_invalid(self):
        self.assertIsNone(quiz.score(["<script>", ""]))

    def test_result_page_and_session(self):
        PortfolioProject.objects.create(
            title="Gold Lounge", room_type="living", style="luxury", budget_band="above_40", location="Indore",
            summary="s", description="d", cover=SimpleUploadedFile("a.jpg", TINY_JPG, "image/jpeg"))
        answers = {q["key"]: "luxury" for q in quiz.QUESTIONS}
        r = self.client.post(reverse("website:quiz_result"), answers)
        self.assertContains(r, "Gold Lounge")
        self.assertContains(r, "?style=luxury")
        self.assertEqual(self.client.session["quiz_style"], "luxury")
        # The booking page then carries the quiz style.
        self.assertContains(self.client.get(reverse("bookings:book")), 'value="luxury"')

    def test_empty_quiz_redirects(self):
        self.assertRedirects(self.client.post(reverse("website:quiz_result"), {}), reverse("website:quiz"))

    def test_quiz_page_has_five_questions(self):
        r = self.client.get(reverse("website:quiz"))
        self.assertEqual(len(r.context["questions"]), 5)


class MoodboardAndLockedTests(TestCase):
    def test_moodboard(self):
        p = PortfolioProject.objects.create(
            title="Sage Kitchen", room_type="kitchen", style="contemporary", budget_band="under_5", location="Bhopal",
            summary="A bright kitchen", description="d", cover=SimpleUploadedFile("a.jpg", TINY_JPG, "image/jpeg"))
        ProjectSwatch.objects.create(project=p, kind="colour", name="Sage", hex="#7A8B6F")
        r = self.client.get(reverse("website:moodboard", args=[p.slug]))
        self.assertContains(r, "Sage")
        self.assertContains(r, 'data-locked="walkthrough_3d"')

    def test_feature_interest_recorded(self):
        r = self.client.post(reverse("core:feature_interest", args=["online_payments"]))
        self.assertTrue(r.json()["ok"])
        self.assertEqual(FeatureInterest.objects.get().feature, "Online payments (Razorpay)")
        self.assertEqual(self.client.post(reverse("core:feature_interest", args=["nope"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("core:feature_interest", args=["online_payments"])).status_code, 405)
