"""Turn the demo into a fresh, live client instance.

Removes all demo data and demo logins, keeps StudioSettings (name, logo, colours, contact, GST, rates,
modules), creates the owner's login and switches DEMO_MODE off in .env.
"""
import secrets
import string

from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from automations.engine import ensure_templates
from core.demo_reset import DEMO_USERNAMES, set_env, wipe
from core.models import StudioSettings
from core.permissions import OWNER


def _password():
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(14))
        if any(c.isdigit() for c in pw) and any(c.isupper() for c in pw) and any(c.islower() for c in pw):
            return pw


class Command(BaseCommand):
    help = "Prepare a client instance: delete demo data, keep settings, create the owner login, DEMO_MODE off."

    def add_arguments(self, parser):
        parser.add_argument("--owner-username", required=True, help="Login name for the studio owner")
        parser.add_argument("--owner-name", default="", help='Full name, e.g. "Rohit Sharma"')
        parser.add_argument("--owner-email", default="")
        parser.add_argument("--password", help="Owner password (a strong one is generated if omitted)")
        parser.add_argument("--keep-content", action="store_true",
                            help="Keep portfolio, services, FAQs and knowledge base (e.g. after brand_demo with their photos). "
                                 "Sample testimonials are always removed.")
        parser.add_argument("--keep-catalogue", action="store_true", help="Keep the vendors and materials catalogue as a starting point")
        parser.add_argument("--noinput", action="store_true", help="Don't ask for confirmation")

    def handle(self, *args, **o):
        username = o["owner_username"].strip().lower()
        if not username or not username.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise CommandError("--owner-username may contain letters, numbers, dots, - and _ only.")
        if username in DEMO_USERNAMES:
            raise CommandError(f"“{username}” is a demo login name; please choose the owner's own username.")
        if User.objects.filter(username=username).exists():
            raise CommandError(f"A user called “{username}” already exists.")
        password = o["password"] or _password()
        try:
            validate_password(password)
        except ValidationError as e:
            raise CommandError("Password too weak: " + " ".join(e.messages))

        studio = StudioSettings.load()
        if not o["noinput"]:
            self.stdout.write(self.style.WARNING(
                f"This permanently deletes ALL demo data (leads, projects, quotations, invoices, chats, demo logins"
                f"{'' if o['keep_content'] else ', portfolio, services, FAQs, knowledge base'}) for “{studio.name}”."))
            if input("Type YES to continue: ").strip() != "YES":
                raise CommandError("Cancelled — nothing was changed.")

        wipe(keep_content=o["keep_content"], keep_catalogue=o["keep_catalogue"], keep_availability=True,
             client_handover=True, out=self.stdout)
        ensure_templates()

        first, _, last = o["owner_name"].strip().partition(" ")
        owner = User.objects.create_user(username, o["owner_email"], password, first_name=first[:150], last_name=last[:150])
        owner.groups.add(Group.objects.get_or_create(name=OWNER)[0])
        for g in ("Team Member", "Client"):
            Group.objects.get_or_create(name=g)

        env = set_env("DEMO_MODE", "False")
        self.stdout.write(self.style.SUCCESS(f"Client instance ready for “{studio.name}”."))
        self.stdout.write(f"  Owner login: {username}")
        if not o["password"]:
            self.stdout.write(f"  Generated password: {password}   (shown once — share it privately)")
        self.stdout.write(f"  DEMO_MODE=False written to {env} — restart the server for it to take effect.")
        self.stdout.write("  Next: Studio settings (GSTIN, bank, rates, modules), Website content, Availability. "
                          "See docs/NEW_CLIENT_SETUP.md.")
