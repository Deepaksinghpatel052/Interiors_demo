"""Shared clean-up for `reset_demo` (wipe + re-seed) and `setup_client` (wipe + hand over)."""
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from .permissions import CLIENT, TEAM

DEMO_USERNAMES = ["admin", "owner", "designer", "client"]

# media sub-folders written by the demo / by users of the demo (never `demo_photos`, the download cache)
WORK_DIRS = ["documents", "proposals", "site_updates", "requests"]
CONTENT_DIRS = ["portfolio", "services", "knowledge", "tours"]


def _rmtree(rel):
    root = Path(settings.MEDIA_ROOT).resolve()
    path = (root / rel).resolve()
    if root in path.parents and path.exists():
        shutil.rmtree(path, ignore_errors=True)


@transaction.atomic
def wipe(*, keep_content=False, keep_catalogue=False, keep_availability=False, client_handover=False, out=None):
    """Delete business data. Returns a dict of counts. StudioSettings is never touched here."""
    from assistant.models import ChatSession, KnowledgeDocument
    from automations.models import AutomationLog
    from bookings.models import BlockedDate, Booking, WeeklyAvailability
    from crm.models import Lead, LeadActivity
    from finance.models import CatalogueItem, Invoice, Quotation, Vendor
    from studio.models import ClientProject
    from website.models import FAQ, PhotoCredit, PortfolioProject, Service, Testimonial, Tour

    from .models import FeatureInterest, ModuleRequest, ProductEnquiry

    counts = {}

    def drop(label, qs):
        n = qs.count()
        qs.delete()
        counts[label] = n

    drop("chats", ChatSession.objects.all())
    drop("automation log", AutomationLog.objects.all())
    drop("invoices", Invoice.objects.all())
    drop("quotations", Quotation.objects.all())
    drop("projects", ClientProject.objects.all())
    drop("bookings", Booking.objects.all())
    LeadActivity.objects.all().delete()
    drop("leads", Lead.objects.all())
    if not keep_availability:
        BlockedDate.objects.all().delete()
        WeeklyAvailability.objects.all().delete()
    if not keep_catalogue:
        drop("catalogue items", CatalogueItem.objects.all())
        drop("vendors", Vendor.objects.all())
    if keep_content:
        if client_handover:   # samples must never go live as if they were real reviews
            drop("sample testimonials", Testimonial.objects.filter(is_sample=True))
            drop("sample 360° tours", Tour.objects.filter(is_sample=True))
    else:
        drop("knowledge documents", KnowledgeDocument.objects.all())
        drop("portfolio projects", PortfolioProject.objects.all())
        drop("services", Service.objects.all())
        drop("FAQs", FAQ.objects.all())
        drop("testimonials", Testimonial.objects.all())
        drop("360° tours", Tour.objects.all())
        PhotoCredit.objects.all().delete()
    if client_handover:   # the seller's own sales data must not stay on a client's server
        drop("feature-interest clicks", FeatureInterest.objects.all())
        drop("DEVNIXPLUS product enquiries", ProductEnquiry.objects.all())
        drop("extra-feature requests", ModuleRequest.objects.all())

    # people: demo logins, portal clients and team members created during demos
    people = User.objects.filter(username__in=DEMO_USERNAMES) | User.objects.filter(groups__name__in=[CLIENT, TEAM])
    if not client_handover:
        people = people | User.objects.filter(is_superuser=False)
    drop("user accounts", User.objects.filter(pk__in=people.values("pk")))

    transaction.on_commit(lambda: [_rmtree(d) for d in WORK_DIRS + ([] if keep_content else CONTENT_DIRS)])
    _bump_ai_index()
    if out:
        out.write("Removed: " + ", ".join(f"{v} {k}" for k, v in counts.items() if v) + ".")
    return counts


def _bump_ai_index():
    try:
        from assistant import rag
        rag.bump_version()
    except Exception:  # the index is rebuilt lazily anyway
        pass


def set_env(key, value, env_path=None):
    """Set KEY=value in .env (adds the line if missing). Returns the path written."""
    path = Path(env_path or Path(settings.BASE_DIR) / ".env")
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    done = False
    for i, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key:
            lines[i] = f"{key}={value}"
            done = True
    if not done:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
