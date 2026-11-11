import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class WeeklyAvailability(models.Model):
    """A bookable window on a weekday, e.g. Monday 10:00–13:00 in 60-minute slots."""

    class Weekday(models.IntegerChoices):
        MON = 0, "Monday"
        TUE = 1, "Tuesday"
        WED = 2, "Wednesday"
        THU = 3, "Thursday"
        FRI = 4, "Friday"
        SAT = 5, "Saturday"
        SUN = 6, "Sunday"

    weekday = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name_plural = "Weekly availability"

    def __str__(self):
        return f"{self.get_weekday_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"


class BlockedDate(models.Model):
    date = models.DateField(unique=True)
    reason = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date:%d-%m-%Y} {self.reason}"


def make_reference():
    return "BK-" + "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))


class Booking(models.Model):
    class Mode(models.TextChoices):
        ONLINE = "online", "Online video call"
        STUDIO = "studio", "At our studio"
        SITE = "site_visit", "Site visit"

    class Kind(models.TextChoices):
        CONSULTATION = "consultation", "Consultation"
        SITE_VISIT = "site_visit", "Site visit"

    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    reference = models.CharField(max_length=12, unique=True, default=make_reference, editable=False)
    lead = models.ForeignKey("crm.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CONSULTATION)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.STUDIO)
    date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    site_address = models.CharField(max_length=240, blank=True)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]
        constraints = [
            # The database itself refuses a second active booking in the same slot.
            models.UniqueConstraint(fields=["date", "start_time"], condition=~Q(status="cancelled"),
                                    name="unique_active_slot"),
        ]

    def __str__(self):
        return f"{self.reference} · {self.name} · {self.date:%d-%m-%Y} {self.start_time:%I:%M %p}"

    @property
    def start(self):
        return timezone.make_aware(datetime.combine(self.date, self.start_time))

    @property
    def end(self):
        return self.start + timedelta(minutes=self.duration_minutes)
