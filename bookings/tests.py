from datetime import date, datetime, time, timedelta
from unittest import mock

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from crm.models import Lead

from .models import BlockedDate, Booking, WeeklyAvailability
from .slots import bookable_days, is_slot_available, slots_for_date


def next_weekday(wd, after_days=2):
    d = timezone.localdate() + timedelta(days=after_days)
    while d.weekday() != wd:
        d += timedelta(days=1)
    return d


class SlotEngineTests(TestCase):
    def setUp(self):
        for wd in range(6):
            WeeklyAvailability.objects.create(weekday=wd, start_time=time(10), end_time=time(13))
        self.day = next_weekday(1)  # a Tuesday at least 2 days away

    def test_slots_from_availability(self):
        slots = slots_for_date(self.day)
        self.assertEqual([s["time"] for s in slots], ["10:00", "11:00", "12:00"])
        self.assertTrue(all(s["available"] for s in slots))

    def test_sunday_closed(self):
        self.assertEqual(slots_for_date(next_weekday(6)), [])

    def test_blocked_date_has_no_slots(self):
        BlockedDate.objects.create(date=self.day)
        self.assertEqual(slots_for_date(self.day), [])

    def test_booked_slot_unavailable(self):
        Booking.objects.create(date=self.day, start_time=time(11), name="A", mobile="9876543210")
        self.assertFalse(is_slot_available(self.day, time(11)))
        self.assertTrue(is_slot_available(self.day, time(10)))

    def test_cancelled_booking_frees_slot(self):
        Booking.objects.create(date=self.day, start_time=time(11), name="A", mobile="9876543210",
                               status=Booking.Status.CANCELLED)
        self.assertTrue(is_slot_available(self.day, time(11)))

    def test_database_prevents_double_booking(self):
        Booking.objects.create(date=self.day, start_time=time(11), name="A", mobile="9876543210")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(date=self.day, start_time=time(11), name="B", mobile="9876543211")

    def test_past_and_short_notice_slots_unavailable(self):
        day = next_weekday(2)
        now = timezone.make_aware(datetime.combine(day, time(10, 30)))
        slots = {s["time"]: s["available"] for s in slots_for_date(day, now=now)}
        # 10:00 is past, 11:00 is under 2 hours away, 12:00 is still under 2 hours (12:30 cut-off)
        self.assertEqual(slots, {"10:00": False, "11:00": False, "12:00": False})
        now = timezone.make_aware(datetime.combine(day, time(9, 0)))
        self.assertTrue({s["time"]: s["available"] for s in slots_for_date(day, now=now)}["12:00"])

    def test_outside_window_and_past_days(self):
        self.assertEqual(slots_for_date(timezone.localdate() - timedelta(days=1)), [])
        self.assertEqual(slots_for_date(timezone.localdate() + timedelta(days=60)), [])

    def test_bookable_days_skip_full_days(self):
        days = [d["date"] for d in bookable_days()]
        self.assertIn(self.day, days)
        for t in (10, 11, 12):
            Booking.objects.create(date=self.day, start_time=time(t), name="X", mobile="9876543210")
        self.assertNotIn(self.day, [d["date"] for d in bookable_days()])


class BookingFlowTests(TestCase):
    def setUp(self):
        for wd in range(6):
            WeeklyAvailability.objects.create(weekday=wd, start_time=time(10), end_time=time(13))
        self.day = next_weekday(3)

    def post(self, **extra):
        data = {"mode": "studio", "date": self.day.isoformat(), "time": "11:00", "name": "Neha Sharma",
                "mobile": "9876543210", "email": "", "property_type": "2bhk", "budget_band": "5_10",
                "site_address": "", "notes": "Living room", "style": "modern", "website": ""}
        data.update(extra)
        return self.client.post(reverse("bookings:book"), data)

    def test_booking_creates_lead_and_booking(self):
        r = self.post()
        b = Booking.objects.get()
        self.assertRedirects(r, reverse("bookings:confirmed", args=[b.reference]))
        self.assertEqual(b.lead.stage, Lead.Stage.CONSULTATION)
        self.assertEqual(b.lead.style_preference, "modern")
        self.assertTrue(b.lead.activities.filter(text__contains=b.reference).exists())
        page = self.client.get(r.url)
        self.assertContains(page, b.reference)
        self.assertContains(page, "wa.me/")
        self.assertContains(page, "calendar.google.com")

    def test_second_booking_same_slot_rejected(self):
        self.post()
        r = self.post(name="Someone Else", mobile="9876500000")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "no longer available")
        self.assertEqual(Booking.objects.count(), 1)

    def test_site_visit_requires_address(self):
        r = self.post(mode="site_visit")
        self.assertContains(r, "site address")
        self.assertFalse(Booking.objects.exists())

    def test_reuses_open_lead_with_same_mobile(self):
        Lead.objects.create(name="Neha", mobile="9876543210", source=Lead.Source.ESTIMATOR)
        self.post()
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(Lead.objects.get().source, Lead.Source.ESTIMATOR)

    def test_confirmation_and_ics_private_to_booker(self):
        self.post()
        b = Booking.objects.get()
        ics = self.client.get(reverse("bookings:ics", args=[b.reference]))
        self.assertEqual(ics["Content-Type"], "text/calendar; charset=utf-8")
        body = ics.content.decode()
        self.assertIn("BEGIN:VEVENT", body)
        # 11:00 IST == 05:30 UTC
        self.assertIn(f"DTSTART:{self.day:%Y%m%d}T053000Z", body)
        other = self.client_class()
        self.assertEqual(other.get(reverse("bookings:confirmed", args=[b.reference])).status_code, 404)
        self.assertEqual(other.get(reverse("bookings:ics", args=[b.reference])).status_code, 404)

    def test_slots_api(self):
        r = self.client.get(reverse("bookings:api_slots"), {"date": self.day.isoformat()})
        self.assertEqual([s["time"] for s in r.json()["slots"]], ["10:00", "11:00", "12:00"])
        self.assertEqual(self.client.get(reverse("bookings:api_slots"), {"date": "nope"}).status_code, 400)

    def test_book_page_renders_days(self):
        r = self.client.get(reverse("bookings:book") + "?style=luxury&project=Gold+Room")
        self.assertContains(r, self.day.strftime("%Y-%m-%d"))
        self.assertContains(r, "Luxury")
        self.assertContains(r, "Gold Room")
