"""Client portal. Every query is scoped to the signed-in client's own projects (others get 404)."""
import mimetypes
from pathlib import Path

from django import forms
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.permissions import client_required
from core.validators import validate_image
from finance import pdf as finance_pdf
from finance.models import Invoice, Quotation
from studio.client_actions import PortalError, add_comment, approve_proposal, raise_request, request_changes
from studio.models import ClientProject, ClientRequest, DesignProposal, Milestone, ProjectDocument

SESSION_KEY = "portal_project"


def _projects(request):
    return ClientProject.objects.filter(client=request.user).select_related("designer").order_by("-start_date")


def _current(request):
    projects = list(_projects(request))
    if not projects:
        return None, []
    wanted = request.GET.get("p") or request.session.get(SESSION_KEY)
    current = next((p for p in projects if str(p.pk) == str(wanted)), projects[0])
    request.session[SESSION_KEY] = current.pk
    return current, projects


def _ctx(request, project, projects, **extra):
    waiting = project.proposals.filter(status=DesignProposal.Status.SHARED).count() if project else 0
    due = [i for i in project.invoices.filter(status__in=["issued", "partial"]).prefetch_related("payments")] if project else []
    return {"project": project, "projects": projects, "waiting_designs": waiting,
            "due_invoices": due, "due_total": sum((i.balance for i in due), 0), **extra}


def portal_view(fn):
    """Decorator: client only, and a current project must exist."""
    @client_required
    def wrapper(request, *args, **kwargs):
        project, projects = _current(request)
        if project is None:
            return render(request, "portal/no_project.html")
        return fn(request, project, projects, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


# ------------------------------------------------------------------------------ overview
@portal_view
def overview(request, project, projects):
    milestones = list(project.milestones.all())
    latest_update = project.updates.prefetch_related("photos").first()
    shared = project.proposals.exclude(status=DesignProposal.Status.DRAFT).first()
    return render(request, "portal/overview.html", _ctx(
        request, project, projects, milestones=milestones, next_milestone=project.next_milestone,
        latest_update=latest_update, latest_design=shared,
        open_requests=project.requests.exclude(status=ClientRequest.Status.RESOLVED).count(),
        today=timezone.localdate()))


# ------------------------------------------------------------------------------ designs
@portal_view
def designs(request, project, projects):
    proposals = project.proposals.exclude(status=DesignProposal.Status.DRAFT).prefetch_related("images")
    return render(request, "portal/designs.html", _ctx(request, project, projects, proposals=proposals))


@portal_view
def design_detail(request, project, projects, pk):
    proposal = get_object_or_404(project.proposals.exclude(status=DesignProposal.Status.DRAFT), pk=pk)
    latest_version = project.proposals.exclude(status=DesignProposal.Status.DRAFT).order_by("-version").values_list("version", flat=True).first()
    return render(request, "portal/design_detail.html", _ctx(
        request, project, projects, proposal=proposal, images=proposal.images.all(),
        comments=proposal.comments.select_related("author", "image"),
        is_latest=proposal.version == latest_version))


@portal_view
@require_POST
def design_action(request, project, projects, pk):
    proposal = get_object_or_404(project.proposals.exclude(status=DesignProposal.Status.DRAFT), pk=pk)
    action, text = request.POST.get("action"), request.POST.get("text", "")
    try:
        if action == "approve":
            approve_proposal(proposal, request.user, text)
            messages.success(request, f"Thank you! Design v{proposal.version} is approved — we’ll start the next step.")
        elif action == "changes":
            request_changes(proposal, request.user, text)
            messages.success(request, "Got it. Your designer will share a revised version soon.")
        elif action == "comment":
            image_id = request.POST.get("image")
            add_comment(proposal, request.user, text, int(image_id) if (image_id or "").isdigit() else None)
            messages.success(request, "Comment added. Your designer has been notified.")
        else:
            raise PortalError("Unknown action.")
    except PortalError as e:
        messages.error(request, str(e))
    return redirect("portal:design_detail", pk=proposal.pk)


# ------------------------------------------------------------------------------ timeline, updates, documents, payments
@portal_view
def timeline(request, project, projects):
    return render(request, "portal/timeline.html", _ctx(
        request, project, projects, milestones=project.milestones.all(), today=timezone.localdate()))


@portal_view
def updates(request, project, projects):
    return render(request, "portal/updates.html", _ctx(
        request, project, projects, updates=project.updates.prefetch_related("photos").select_related("author")))


@portal_view
def documents(request, project, projects):
    quotations = project.quotations.filter(status__in=[Quotation.Status.SENT, Quotation.Status.ACCEPTED])
    return render(request, "portal/documents.html", _ctx(
        request, project, projects, quotations=quotations,
        invoices=project.invoices.exclude(status=Invoice.Status.CANCELLED),
        documents=project.documents.filter(visible_to_client=True)))


@portal_view
def document_download(request, project, projects, pk):
    doc = get_object_or_404(ProjectDocument, pk=pk, project=project, visible_to_client=True)
    path = Path(doc.file.path)
    if not path.exists():
        raise Http404
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    resp = FileResponse(path.open("rb"), content_type=ctype, as_attachment=ctype != "application/pdf",
                        filename=path.name)
    resp["X-Content-Type-Options"] = "nosniff"
    return resp


@portal_view
def quotation_pdf(request, project, projects, pk):
    q = get_object_or_404(project.quotations.filter(status__in=[Quotation.Status.SENT, Quotation.Status.ACCEPTED]), pk=pk)
    return finance_pdf.quotation_pdf(q)


@portal_view
def invoice_pdf(request, project, projects, pk):
    inv = get_object_or_404(project.invoices.exclude(status=Invoice.Status.CANCELLED), pk=pk)
    return finance_pdf.invoice_pdf(inv)


@portal_view
def payments(request, project, projects):
    schedule = list(project.schedule.prefetch_related("invoices__payments"))
    invoices = [i for i in project.invoices.prefetch_related("payments") if i.status != Invoice.Status.CANCELLED]
    contract = sum((s.amount for s in schedule), 0)
    paid = sum((i.paid for i in invoices), 0)
    return render(request, "portal/payments.html", _ctx(
        request, project, projects, schedule=schedule, invoices=invoices, contract=contract, paid=paid,
        pct=round(100 * float(paid) / float(contract)) if contract else 0))


# ------------------------------------------------------------------------------ requests / snags
class RequestForm(forms.Form):
    title = forms.CharField(max_length=140, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Wardrobe shutter not closing properly"}))
    description = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Where is it and what happens?"}))
    photo = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*", "capture": "environment"}))
    urgent = forms.BooleanField(required=False, label="This is urgent", widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))

    def clean_photo(self):
        f = self.cleaned_data.get("photo")
        if f:
            validate_image(f)
        return f


@portal_view
def requests_view(request, project, projects):
    form = RequestForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            d = form.cleaned_data
            try:
                raise_request(project, request.user, d["title"], d["description"], d["photo"], d["urgent"])
                messages.success(request, "Request sent. Your designer will get back to you soon.")
                return redirect("portal:requests")
            except PortalError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Please check the request details.")
    return render(request, "portal/requests.html", _ctx(
        request, project, projects, form=form, requests=project.requests.select_related("task")))
