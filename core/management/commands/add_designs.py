"""Add the extra portfolio designs (core/demo_more_designs.py) to an existing database.

Only adds designs that are missing (matched by title) and only touches those designs:
leads, bookings, client projects and anything the studio has edited stay as they are.

    python manage.py add_designs
    docker compose exec web python manage.py add_designs      # on the server
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core import demo_data as D
from core import photos
from core.demo_more_designs import MORE_PROJECTS
from core.management.commands.seed_demo import Command as SeedDemo
from website.models import PortfolioProject


class Command(BaseCommand):
    help = "Add the extra demo portfolio designs (19 -> 64) without changing anything else."

    @transaction.atomic
    def handle(self, *args, **opts):
        missing = [row for row in MORE_PROJECTS
                   if not PortfolioProject.objects.filter(title=row[0]).exists()]
        if not missing:
            self.stdout.write(f"All extra designs are already there ({PortfolioProject.objects.count()} designs).")
            return
        seed = SeedDemo(stdout=self.stdout, stderr=self.stderr)
        seed.seed_portfolio(rows=missing, start=len(D.PROJECTS) - len(MORE_PROJECTS))

        used, real = set(), 0
        for project in PortfolioProject.objects.filter(title__in=[row[0] for row in missing]):
            real += photos.apply_project(project, used)
        credits = photos.add_credits(used)
        self.stdout.write(self.style.SUCCESS(
            f"Added {len(missing)} designs ({real} with real photos, {credits} new photo credits). "
            f"Portfolio now has {PortfolioProject.objects.count()} designs."))
