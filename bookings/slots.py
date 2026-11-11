"""Slot engine: turns weekly availability into bookable slots, minus blocked dates,
existing bookings and times too close to now."""
from datetime import date, datetime, time, timedelta

from django.utils import timezone

from .models import BlockedDate, Booking, WeeklyAvailability

MIN_NOTICE = timedelta(hours=2)
BOOKING_WINDOW_DAYS = 21


def _now():
    return timezone.localtime()


def slots_for_date(day: date, now=None):
    """Return a list of {"time": "HH:MM", "label": "10:00 AM", "available": bool} for one day."""
    now = now or _now()
    if day < now.date() or day > now.date() + timedelta(days=BOOKING_WINDOW_DAYS):
        return []
    if BlockedDate.objects.filter(date=day).exists():
        return []
    taken = set(Booking.objects.filter(date=day).exclude(status=Booking.Status.CANCELLED)
                .values_list("start_time", flat=True))
    out = []
    for window in WeeklyAvailability.objects.filter(weekday=day.weekday(), is_active=True):
        step = timedelta(minutes=window.slot_minutes)
        cur = datetime.combine(day, window.start_time)
        end = datetime.combine(day, window.end_time)
        while cur + step <= end:
            t = cur.time()
            aware = timezone.make_aware(cur)
            out.append({
                "time": t.strftime("%H:%M"),
                "label": cur.strftime("%I:%M %p").lstrip("0"),
                "available": t not in taken and aware >= now + MIN_NOTICE,
            })
            cur += step
    out.sort(key=lambda s: s["time"])
    return out


def is_slot_available(day: date, start: time, now=None) -> bool:
    key = start.strftime("%H:%M")
    return any(s["time"] == key and s["available"] for s in slots_for_date(day, now))


def bookable_days(now=None, count=14):
    """Next `count` days that have at least one free slot."""
    now = now or _now()
    days, d = [], now.date()
    limit = now.date() + timedelta(days=BOOKING_WINDOW_DAYS)
    while d <= limit and len(days) < count:
        slots = slots_for_date(d, now)
        free = sum(s["available"] for s in slots)
        if free:
            days.append({"date": d, "free": free})
        d += timedelta(days=1)
    return days
