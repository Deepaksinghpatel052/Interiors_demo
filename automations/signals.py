import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from bookings.models import Booking
from crm.models import Lead

from . import engine

log = logging.getLogger(__name__)


@receiver(post_save, sender=Booking)
def booking_saved(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        try:
            engine.booking_created(instance)
        except Exception:  # an automation must never block a booking
            log.exception("booking automation failed")


@receiver(post_save, sender=Lead)
def lead_saved(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        try:
            engine.lead_created(instance)
        except Exception:
            log.exception("lead automation failed")
