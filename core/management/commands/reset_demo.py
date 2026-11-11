"""Wipe everything prospects touched during demos and seed fresh data (run nightly in demo mode)."""
import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from django.core.cache import cache

from automations.models import MessageTemplate
from core.demo_reset import _rmtree, wipe
from core.models import CACHE_KEY, StudioSettings


class Command(BaseCommand):
    help = "Reset the demo: delete leads, bookings, projects, quotations, chats and demo logins, then re-seed."

    def add_arguments(self, parser):
        parser.add_argument("--full", action="store_true",
                            help="Also restore the default Aangan Interiors branding and module switches "
                                 "(otherwise the current name, logo, colours and modules are kept).")
        parser.add_argument("--offline", action="store_true", help="Don't try to download missing demo photos.")
        parser.add_argument("--force", action="store_true", help="Allow running when DEMO_MODE is off (dangerous).")

    def handle(self, *args, **opts):
        if not settings.DEMO_MODE and not opts["force"]:
            raise CommandError("DEMO_MODE is off — this looks like a live client site. Refusing to delete data. "
                               "Use --force only if you are sure.")
        started = time.monotonic()
        wipe(out=self.stdout)
        MessageTemplate.objects.all().delete()          # prospects may have edited them during a call
        if opts["full"]:
            StudioSettings.objects.all().delete()
            _rmtree("brand")                              # old prospect logos
            cache.delete(CACHE_KEY)                       # load() recreates the defaults
            self.stdout.write("Branding and modules restored to the Aangan Interiors defaults.")
        call_command("seed_demo", offline=opts["offline"], stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(f"Demo reset in {time.monotonic() - started:.0f} s."))
