import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.models import StudioSettings
from core.permissions import CLIENT, OWNER, TEAM
from crm.models import Lead
from crm.services import convert_lead

from . import services
from .models import CatalogueItem, Invoice, Quotation, financial_year
from .services import FinanceError, amount_in_words


def user(name, group):
    u = User.objects.create_user(username=name, password="pw12345!")
    u.groups.add(Group.objects.get_or_create(name=group)[0])
    return u


def payload(*rooms):
    return {"title": "Test", "rooms": [{"name": name, "items": items} for name, items in rooms]}


def item(desc, qty, rate, gst=18, disc=0, unit="nos"):
    return {"description": desc, "quantity": str(qty), "rate": str(rate), "gst_percent": str(gst),
            "discount_percent": str(disc), "unit": unit}


class FinanceBase(TestCase):
    def setUp(self):
        self.owner = user("own", OWNER)
        self.team = user("tm", TEAM)
        self.client_user = user("cl", CLIENT)
        self.lead = Lead.objects.create(name="Neha Sharma", mobile="9876543210", property_type="2bhk")
        self.project, _, _ = convert_lead(self.lead, self.owner)

    def quote(self, *rooms, inter_state=False):
        q = services.create_quotation(project=self.project, user=self.owner)
        data = payload(*rooms)
        data["inter_state"] = inter_state
        services.save_builder(q, data)
        q.refresh_from_db()
        return q


class TotalsAndGstTests(FinanceBase):
    def test_line_and_quotation_totals(self):
        q = self.quote(("Kitchen", [item("Base unit", 12.5, 9600, disc=5), item("Quartz", 40, 720)]),
                       ("Living", [item("Curtains", 18, 680, gst=12)]))
        # Base: 12.5×9600 = 1,20,000 − 5% = 1,14,000 ; GST 18% = 20,520
        # Quartz: 40×720 = 28,800 ; GST 5,184
        # Curtains: 18×680 = 12,240 ; GST 12% = 1,468.80
        self.assertEqual(q.subtotal, Decimal("161040.00"))
        self.assertEqual(q.discount_total, Decimal("6000.00"))
        self.assertEqual(q.taxable_total, Decimal("155040.00"))
        self.assertEqual(q.gst_total, Decimal("27172.80"))
        self.assertEqual(q.grand_total, Decimal("182213"))
        self.assertEqual(q.round_off, Decimal("0.20"))
        self.assertEqual(q.cgst + q.sgst, q.gst_total)
        self.assertEqual(q.cgst, Decimal("13586.40"))
        self.assertEqual(q.igst, 0)
        self.assertEqual([r for r, _, _ in q.gst_breakdown()], [Decimal("12.00"), Decimal("18.00")])

    def test_inter_state_uses_igst(self):
        q = self.quote(("Office", [item("Workstation", 10, 14500)]), inter_state=True)
        self.assertEqual((q.cgst, q.sgst, q.igst), (0, 0, Decimal("26100.00")))
        self.assertEqual(q.grand_total, Decimal("171100"))

    def test_odd_gst_split_keeps_total(self):
        q = self.quote(("Room", [item("Lamp", 1, 0.55, gst=18)]))  # GST 0.10 -> 0.05 + 0.05
        self.assertEqual(q.cgst + q.sgst, q.gst_total)

    def test_builder_validation(self):
        q = services.create_quotation(project=self.project)
        for bad in [item("", 1, 100), item("X", 0, 100), item("X", 1, -5), item("X", 1, 100, disc=120),
                    item("X", 1, 100, gst=40), item("X", "abc", 100)]:
            with self.subTest(bad=bad), self.assertRaises(FinanceError):
                services.save_builder(q, payload(("Room", [bad])))

    def test_only_drafts_editable(self):
        q = self.quote(("Room", [item("Lamp", 1, 1000)]))
        services.send_quotation(q)
        with self.assertRaises(FinanceError):
            services.save_builder(q, payload(("Room", [item("Lamp", 2, 1000)])))


class NumberingTests(FinanceBase):
    def test_financial_year(self):
        self.assertEqual(financial_year(date(2026, 4, 1)), "2026-27")
        self.assertEqual(financial_year(date(2027, 3, 31)), "2026-27")
        self.assertEqual(financial_year(date(2026, 3, 31)), "2025-26")

    def _accepted_items(self):
        q = self.quote(("Room", [item("Lamp", 1, 100000)]))
        services.send_quotation(q)
        return services.accept_quotation(q, self.owner)

    def test_invoice_series_per_financial_year(self):
        items = self._accepted_items()
        a = services.raise_invoice(items[0], on_date=date(2026, 3, 20))
        b = services.raise_invoice(items[1], on_date=date(2026, 4, 2))
        c = services.raise_invoice(items[2], on_date=date(2026, 4, 9))
        self.assertEqual([a.number, b.number, c.number], ["INV/2025-26/0001", "INV/2026-27/0001", "INV/2026-27/0002"])

    def test_no_duplicate_invoice_for_milestone(self):
        items = self._accepted_items()
        services.raise_invoice(items[0])
        with self.assertRaises(FinanceError):
            services.raise_invoice(items[0])

    def test_quotation_numbers_increment(self):
        a = services.create_quotation(project=self.project)
        b = services.create_quotation(lead=self.lead)
        self.assertNotEqual(a.number, b.number)
        self.assertTrue(b.number.endswith("/002"))


class AcceptanceAndPaymentTests(FinanceBase):
    def test_accept_creates_schedule_that_adds_up(self):
        q = self.quote(("Room", [item("Wardrobe", 1, 123457)]))  # total with GST = 1,45,679.26 -> 1,45,679
        services.send_quotation(q)
        items = services.accept_quotation(q, self.owner)
        self.assertEqual([i.label for i in items], [r["label"] for r in StudioSettings.load().payment_schedule])
        self.assertEqual(sum(i.amount for i in items), q.grand_total)
        q.refresh_from_db()
        self.assertEqual(q.status, Quotation.Status.ACCEPTED)
        with self.assertRaises(FinanceError):  # second acceptance for same project
            q2 = self.quote(("Room", [item("X", 1, 10)]))
            services.send_quotation(q2)
            services.accept_quotation(q2)

    def test_accept_requires_project(self):
        q = services.create_quotation(lead=Lead.objects.create(name="Lead Only", mobile="9876500000"))
        services.save_builder(q, payload(("Room", [item("X", 1, 1000)])))
        services.send_quotation(q)
        with self.assertRaises(FinanceError):
            services.accept_quotation(q)

    def test_invoice_split_and_payments(self):
        q = self.quote(("Room", [item("Work", 1, 100000)]))  # 1,18,000 incl. GST
        services.send_quotation(q)
        items = services.accept_quotation(q, self.owner)
        inv = services.raise_invoice(items[1])  # 40% = 47,200
        self.assertEqual(inv.total, Decimal("47200.00"))
        self.assertEqual(inv.taxable_amount, Decimal("40000.00"))
        self.assertEqual(inv.cgst + inv.sgst, Decimal("7200.00"))
        services.record_payment(inv, amount="20000", mode="upi")
        inv.refresh_from_db()
        self.assertEqual((inv.status, inv.balance), (Invoice.Status.PARTIAL, Decimal("27200.00")))
        with self.assertRaises(FinanceError):
            services.record_payment(inv, amount="30000", mode="upi")  # more than balance
        services.record_payment(inv, amount="27200", mode="cash")
        inv.refresh_from_db()
        self.assertEqual(inv.status, Invoice.Status.PAID)

    def test_revision_flow(self):
        q = self.quote(("Room", [item("Work", 1, 50000)]))
        services.send_quotation(q)
        services.reject_quotation(q)
        v2 = services.revise_quotation(q)
        q.refresh_from_db()
        self.assertEqual((v2.number, v2.version, v2.status), (q.number, 2, Quotation.Status.DRAFT))
        self.assertEqual(q.status, Quotation.Status.SUPERSEDED)
        self.assertEqual(v2.grand_total, q.grand_total)
        self.assertEqual(v2.items().count(), 1)


class WordsTests(TestCase):
    def test_amount_in_words(self):
        self.assertEqual(amount_in_words(125450), "Rupees One Lakh Twenty Five Thousand Four Hundred Fifty Only")
        self.assertEqual(amount_in_words("1608937"), "Rupees Sixteen Lakh Eight Thousand Nine Hundred Thirty Seven Only")
        self.assertEqual(amount_in_words("12000000.50"), "Rupees One Crore Twenty Lakh and Fifty Paise Only")
        self.assertEqual(amount_in_words(0), "Rupees Zero Only")


class ViewTests(FinanceBase):
    def test_builder_save_and_pdf(self):
        self.client.force_login(self.team)
        q = services.create_quotation(project=self.project)
        r = self.client.post(reverse("finance:quotation_save", args=[q.pk]),
                             json.dumps(payload(("Kitchen", [item("Base unit", 2, 9600)]))), content_type="application/json")
        self.assertEqual(r.json()["totals"]["grand_total"], "22656.00")
        r = self.client.get(reverse("finance:quotation_pdf", args=[q.pk]))
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        bad = self.client.post(reverse("finance:quotation_save", args=[q.pk]), "not json", content_type="application/json")
        self.assertEqual(bad.status_code, 400)

    def test_invoice_pdf(self):
        q = self.quote(("Room", [item("Work", 1, 10000)]))
        services.send_quotation(q)
        inv = services.raise_invoice(services.accept_quotation(q)[0])
        self.client.force_login(self.owner)
        r = self.client.get(reverse("finance:invoice_pdf", args=[inv.pk]))
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_permissions(self):
        q = self.quote(("Room", [item("Work", 1, 10000)]))
        services.send_quotation(q)
        self.client.force_login(self.client_user)
        for url in [reverse("finance:quotations"), reverse("finance:invoices"), reverse("finance:vendors"),
                    reverse("finance:catalogue"), reverse("finance:quotation_pdf", args=[q.pk])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.team)
        self.assertEqual(self.client.post(reverse("finance:quotation_accept", args=[q.pk])).status_code, 403)
        for url in ["finance:quotations", "finance:invoices", "finance:vendors", "finance:catalogue", "finance:quotation_new"]:
            self.assertEqual(self.client.get(reverse(url)).status_code, 200)
        self.client.force_login(self.owner)
        self.client.post(reverse("finance:quotation_accept", args=[q.pk]))
        q.refresh_from_db()
        self.assertEqual(q.status, Quotation.Status.ACCEPTED)
        r = self.client.get(self.project.get_absolute_url() + "?tab=billing")
        self.assertContains(r, "Raise invoice")

    def test_catalogue_gst_slab_validation(self):
        self.client.force_login(self.team)
        self.client.post(reverse("finance:catalogue"), {"name": "Lamp", "category": "lighting", "unit": "nos",
                                                         "rate": "500", "gst_percent": "17", "is_active": "on"})
        self.assertFalse(CatalogueItem.objects.exists())
        self.client.post(reverse("finance:catalogue"), {"name": "Lamp", "category": "lighting", "unit": "nos",
                                                         "rate": "500", "gst_percent": "18", "is_active": "on"})
        self.assertTrue(CatalogueItem.objects.filter(name="Lamp").exists())

    def test_dashboard_money_kpis_update_after_payment(self):
        q = self.quote(("Room", [item("Work", 1, 100000)]))
        services.send_quotation(q)
        inv = services.raise_invoice(services.accept_quotation(q)[0])
        self.client.force_login(self.owner)
        before = self.client.get(reverse("studio:dashboard")).context["kpis"]
        self.assertEqual(before["pending_payments"], inv.total)
        self.client.post(reverse("finance:invoice_pay", args=[inv.pk]),
                         {"amount": str(inv.total), "date": date.today().isoformat(), "mode": "upi"})
        after = self.client.get(reverse("studio:dashboard")).context["kpis"]
        self.assertEqual(after["pending_payments"], 0)
        self.assertEqual(after["revenue_month"], inv.total)
