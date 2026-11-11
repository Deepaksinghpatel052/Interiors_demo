"""Save the current database as docker/initial_data/data.json.gz.

Docker loads this file on a server's first start (empty database), after running migrations, so the
server starts with exactly the same data as this computer. Photos/uploads ship in media/ alongside it.

    python manage.py snapshot_data            # then commit docker/initial_data/ and media/
"""
import gzip
import io
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command

DEFAULT = Path(settings.BASE_DIR) / "docker" / "initial_data" / "data.json.gz"
# Rebuilt by migrate (contenttypes, permissions) or not worth shipping (sessions, admin history).
EXCLUDE = ["contenttypes", "auth.permission", "sessions", "admin.logentry"]


class Command(BaseCommand):
    help = "Save the database to docker/initial_data/data.json.gz for Docker's first start."

    def add_arguments(self, parser):
        parser.add_argument("--output", default=str(DEFAULT))

    def handle(self, *args, **opts):
        out = Path(opts["output"])
        out.parent.mkdir(parents=True, exist_ok=True)
        buf = io.StringIO()
        call_command("dumpdata", *[], exclude=EXCLUDE, natural_foreign=True, natural_primary=True,
                     indent=None, stdout=buf)
        with gzip.open(out, "wt", encoding="utf-8") as f:
            f.write(buf.getvalue())
        self.stdout.write(self.style.SUCCESS(
            f"Saved {out} ({out.stat().st_size // 1024} KB). Commit it together with the media/ folder."))
