from django.core.management.base import BaseCommand

from automations.engine import run_scheduled


class Command(BaseCommand):
    help = "Daily automation checks: consultation reminders, payment-due reminders, lead follow-ups (simulated)."

    def handle(self, *args, **opts):
        made = run_scheduled()
        self.stdout.write(self.style.SUCCESS(f"Prepared {len(made)} messages (logged, not sent)."))
