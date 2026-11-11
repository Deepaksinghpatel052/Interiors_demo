"""Things a client does from the portal. Each one is visible to the studio straight away."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import ClientRequest, DesignProposal, Milestone, ProposalComment, Task


class PortalError(ValueError):
    pass


@transaction.atomic
def approve_proposal(proposal: DesignProposal, user, comment=""):
    if proposal.status not in (DesignProposal.Status.SHARED, DesignProposal.Status.CHANGES):
        raise PortalError("This design isn't waiting for your approval.")
    newer = proposal.project.proposals.filter(version__gt=proposal.version).exclude(status=DesignProposal.Status.DRAFT)
    if newer.exists():
        raise PortalError("A newer version of this design has been shared. Please review the latest one.")
    proposal.status = DesignProposal.Status.APPROVED
    proposal.decided_at = timezone.now()
    proposal.decision_comment = (comment or "Approved.").strip()[:1500]
    proposal.save(update_fields=["status", "decided_at", "decision_comment"])
    # Move the project forward: the "Design approval" milestone is done.
    ms = proposal.project.milestones.filter(title__icontains="approval").exclude(status=Milestone.Status.DONE).first()
    if ms:
        ms.status, ms.completed_on = Milestone.Status.DONE, timezone.localdate()
        ms.save(update_fields=["status", "completed_on"])
        nxt = proposal.project.milestones.filter(status=Milestone.Status.PENDING).order_by("order").first()
        if nxt:
            nxt.status = Milestone.Status.IN_PROGRESS
            nxt.save(update_fields=["status"])
    return proposal


@transaction.atomic
def request_changes(proposal: DesignProposal, user, comment):
    comment = (comment or "").strip()
    if len(comment) < 5:
        raise PortalError("Please tell us what you’d like to change.")
    if proposal.status != DesignProposal.Status.SHARED:
        raise PortalError("This design isn't waiting for your feedback.")
    proposal.status = DesignProposal.Status.CHANGES
    proposal.decided_at = timezone.now()
    proposal.decision_comment = comment[:1500]
    proposal.save(update_fields=["status", "decided_at", "decision_comment"])
    Task.objects.create(project=proposal.project, title=f"Revise design v{proposal.version}: client requested changes",
                        notes=comment[:1500], assigned_to=proposal.project.designer, from_client=True,
                        due_date=timezone.localdate() + timedelta(days=3), priority=Task.Priority.HIGH)
    return proposal


def add_comment(proposal: DesignProposal, user, text, image_id=None):
    text = (text or "").strip()
    if not text:
        raise PortalError("Please write a comment.")
    if proposal.status == DesignProposal.Status.DRAFT:
        raise PortalError("This design hasn't been shared yet.")
    image = proposal.images.filter(pk=image_id).first() if image_id else None
    if image_id and not image:
        raise PortalError("That image doesn't belong to this design.")
    return ProposalComment.objects.create(proposal=proposal, image=image, author=user, text=text[:1500])


@transaction.atomic
def raise_request(project, user, title, description="", photo=None, urgent=False):
    title = (title or "").strip()
    if len(title) < 3:
        raise PortalError("Please give your request a short title.")
    task = Task.objects.create(project=project, title=f"Client request: {title[:150]}", notes=description[:2000],
                               assigned_to=project.designer, from_client=True, created_by=user,
                               due_date=timezone.localdate() + timedelta(days=1 if urgent else 3),
                               priority=Task.Priority.HIGH if urgent else Task.Priority.NORMAL)
    return ClientRequest.objects.create(project=project, raised_by=user, title=title[:140], description=description[:2000],
                                        photo=photo or "", task=task)


def client_events(since, projects=None):
    """Client activity after `since` for the studio's live alerts: approvals, change requests, comments, requests."""
    from core.permissions import is_client
    events = []
    proposals = DesignProposal.objects.filter(decided_at__gt=since).select_related("project")
    comments = ProposalComment.objects.filter(created_at__gt=since).select_related("proposal__project", "author")
    requests = ClientRequest.objects.filter(created_at__gt=since).select_related("project")
    if projects is not None:
        proposals, comments, requests = (proposals.filter(project__in=projects),
                                         comments.filter(proposal__project__in=projects),
                                         requests.filter(project__in=projects))
    for p in proposals:
        verb = "approved" if p.status == DesignProposal.Status.APPROVED else "requested changes to"
        events.append({"at": p.decided_at, "kind": "approved" if verb == "approved" else "changes",
                       "text": f"{p.project.client_name} {verb} design v{p.version}",
                       "url": f"{p.project.get_absolute_url()}?tab=designs"})
    for c in comments:
        if c.author and is_client(c.author):
            events.append({"at": c.created_at, "kind": "comment",
                           "text": f"{c.proposal.project.client_name} commented on design v{c.proposal.version}",
                           "url": f"{c.proposal.project.get_absolute_url()}?tab=designs"})
    for r in requests:
        events.append({"at": r.created_at, "kind": "request", "text": f"{r.project.client_name} raised a request: {r.title}",
                       "url": f"{r.project.get_absolute_url()}?tab=tasks"})
    return sorted(events, key=lambda e: e["at"], reverse=True)
