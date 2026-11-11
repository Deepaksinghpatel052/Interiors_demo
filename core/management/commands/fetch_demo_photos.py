from django.core.management.base import BaseCommand

from core import photos


class Command(BaseCommand):
    help = ("Download the curated royalty-free (CC0) interior photos for the demo and put them on the "
            "portfolio, services, designs and site updates. Leads, bookings and projects are kept.")

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Download again even if already present.")
        parser.add_argument("--no-apply", action="store_true", help="Only download; don't change existing records.")

    def handle(self, *args, **opts):
        self.stdout.write("Downloading demo photos…")
        ok, failed = photos.fetch(self.stdout, force=opts["force"])
        self.stdout.write(f"Downloaded {ok}, failed {len(failed)}.")
        if failed:
            self.stdout.write(self.style.WARNING("Missing photos keep the generated illustrations: " + ", ".join(failed)))
        if not opts["no_apply"]:
            self.stdout.write("Applying photos to demo records…")
            used = photos.apply(self.stdout)
            self.stdout.write(self.style.SUCCESS(f"Done. {used} photos in use; credits saved for /photo-credits/."))
