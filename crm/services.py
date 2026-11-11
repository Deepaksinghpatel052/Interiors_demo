import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils import timezone

from core.permissions import CLIENT
from studio.models import ClientProject, Milestone

from .models import Lead, LeadActivity

DEFAULT_MILESTONES = [
    ("Design & 3D", 14),
    ("Design approval", 21),
    ("Material ordering", 30),
    ("Execution", 70),
    ("Handover", 80),
]


def _unique_username(base):
    base = base or "client"
    name, n = base, 2
    while User.objects.filter(username=name).exists():
        name, n = f"{base}{n}", n + 1
    return name


@transaction.atomic
def convert_lead(lead: Lead, by_user=None):
    """Lead → client login + project with default milestones. Returns (project, username, password).
    Idempotent: converting twice returns the existing project and no new password."""
    if hasattr(lead, "project") and lead.project:
        return lead.project, None, None

    username = _unique_username(f"c{lead.mobile}")
    # Demo: a memorable password. Live: a random one shown once to the owner.
    password = "demo12345" if settings.DEMO_MODE else secrets.token_urlsafe(8)
    first, _, last = lead.name.partition(" ")
    user = User.objects.create_user(username=username, password=password, email=lead.email,
                                    first_name=first, last_name=last)
    user.groups.add(Group.objects.get_or_create(name=CLIENT)[0])

    start = timezone.localdate()
    project = ClientProject.objects.create(
        name=f"{lead.name.split()[0]}’s {lead.get_property_type_display() or 'home'}".strip(),
        lead=lead, client=user, client_name=lead.name, client_mobile=lead.mobile, client_email=lead.email,
        designer=lead.assigned_to or by_user, property_type=lead.property_type,
        site_address=lead.city, start_date=start, target_date=start + timedelta(days=DEFAULT_MILESTONES[-1][1]),
        notes=lead.message)
    for i, (title, days) in enumerate(DEFAULT_MILESTONES):
        Milestone.objects.create(project=project, title=title, due_date=start + timedelta(days=days), order=i,
                                 status=Milestone.Status.IN_PROGRESS if i == 0 else Milestone.Status.PENDING)

    lead.stage = Lead.Stage.WON
    lead.save(update_fields=["stage", "updated_at"])
    LeadActivity.objects.create(lead=lead, user=by_user,
                                text=f"Converted to client · project {project.code} · portal login “{username}”")
    return project, username, password


def move_lead(lead: Lead, stage: str, by_user=None):
    if stage not in Lead.Stage.values or stage == lead.stage:
        return False
    old = lead.get_stage_display()
    lead.stage = stage
    lead.save(update_fields=["stage", "updated_at"])
    LeadActivity.objects.create(lead=lead, user=by_user, text=f"Moved from {old} to {lead.get_stage_display()}")
    return True
