import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from bookings.models import BlockedDate, Booking, WeeklyAvailability
from core.permissions import is_owner, owner_required, team_required
from crm.models import Lead, LeadActivity
from crm.services import convert_lead, move_lead

from . import metrics
from .forms import (AvailabilityFormSet, BlockedDateForm, DocumentForm, LeadForm, MilestoneForm, NoteForm,
                    ProjectForm, ProposalForm, SiteUpdateForm, SpaceForm, TaskForm)
from .models import (ClientProject, DesignProposal, Milestone, ProjectDocument, ProjectSpace, ProposalImage,
                     SiteUpdate, SiteUpdatePhoto, Task)


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except ValueError:
        return None


# ===================================================================== dashboard
@team_required
def dashboard(request):
    from .client_actions import client_events
    overdue = metrics.overdue()
    return render(request, "studio/dashboard.html", {
        "client_feed": client_events(timezone.now() - timedelta(days=14))[:6],
        "kpis": metrics.kpis(),
        "today_date": timezone.localdate(),
        "attention_count": sum(len(v) for v in overdue.values()),
        "charts": {
            "sources": metrics.leads_by_source(),
            "funnel": metrics.funnel(),
            "stages": metrics.projects_by_stage(),
            "revenue": metrics.revenue_by_month(),
        },
        "today": metrics.today_schedule(),
        "overdue": overdue,
        "upcoming": metrics.upcoming_bookings()[:6],
        "activity": metrics.recent_activity(),
    })


# ===================================================================== leads
@team_required
def leads_board(request):
    q, source = request.GET.get("q", "").strip(), request.GET.get("source", "")
    leads = Lead.objects.select_related("assigned_to")
    if q:
        leads = leads.filter(Q(name__icontains=q) | Q(mobile__icontains=q) | Q(city__icontains=q))
    if source in Lead.Source.values:
        leads = leads.filter(source=source)
    columns = [{"value": v, "label": l, "leads": [x for x in leads if x.stage == v]} for v, l in Lead.Stage.choices]
    return render(request, "studio/leads_board.html", {
        "columns": columns, "q": q, "source": source, "sources": Lead.Source.choices,
        "total": len(leads), "today": timezone.localdate()})


@team_required
@require_POST
def lead_move(request):
    data = _json_body(request)
    if not data:
        return HttpResponseBadRequest("Invalid data")
    lead = get_object_or_404(Lead, pk=data.get("lead"))
    stage = data.get("stage")
    if stage not in Lead.Stage.values:
        return HttpResponseBadRequest("Invalid stage")
    changed = move_lead(lead, stage, request.user)
    for i, pk in enumerate(data.get("order", [])[:500]):
        Lead.objects.filter(pk=pk, stage=stage).update(position=i)
    return JsonResponse({"ok": True, "changed": changed, "stage_label": lead.get_stage_display()})


@team_required
def lead_create(request):
    form = LeadForm(request.POST or None, initial={"source": Lead.Source.WALK_IN, "assigned_to": request.user})
    if request.method == "POST" and form.is_valid():
        lead = form.save()
        LeadActivity.objects.create(lead=lead, user=request.user, text="Lead added by the studio")
        messages.success(request, f"Lead “{lead.name}” added.")
        return redirect("studio:lead_detail", pk=lead.pk)
    return render(request, "studio/lead_form.html", {"form": form})


@team_required
def lead_detail(request, pk):
    lead = get_object_or_404(Lead.objects.select_related("assigned_to"), pk=pk)
    form = LeadForm(request.POST or None, instance=lead)
    if request.method == "POST" and form.is_valid():
        changed = form.changed_data
        old_stage = Lead.objects.get(pk=lead.pk).get_stage_display()
        form.save()
        if "stage" in changed:
            LeadActivity.objects.create(lead=lead, user=request.user,
                                        text=f"Moved from {old_stage} to {lead.get_stage_display()}")
        if changed:
            LeadActivity.objects.create(lead=lead, user=request.user, text="Details updated")
        messages.success(request, "Lead saved.")
        return redirect("studio:lead_detail", pk=lead.pk)
    return render(request, "studio/lead_detail.html", {
        "lead": lead, "form": form, "note_form": NoteForm(),
        "activities": lead.activities.select_related("user")[:50],
        "bookings": lead.bookings.all(),
        "project": getattr(lead, "project", None),
    })


@team_required
@require_POST
def lead_note(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    form = NoteForm(request.POST)
    if form.is_valid():
        LeadActivity.objects.create(lead=lead, user=request.user, text=form.cleaned_data["text"])
        lead.save(update_fields=["updated_at"])
        messages.success(request, "Note added.")
    else:
        messages.error(request, "Please write a short note (up to 300 characters).")
    return redirect("studio:lead_detail", pk=pk)


@owner_required
@require_POST
def lead_convert(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    project, username, password = convert_lead(lead, request.user)
    if username:
        messages.success(request, f"{lead.name} is now a client. Project {project.code} created. "
                                  f"Portal login: {username} / {password}")
    else:
        messages.info(request, "This lead was already converted.")
    return redirect(project.get_absolute_url())


# ===================================================================== bookings
@team_required
def bookings_calendar(request):
    return render(request, "studio/bookings_calendar.html", {
        "upcoming": metrics.upcoming_bookings(14),
        "statuses": Booking.Status.choices,
        "blocked": BlockedDate.objects.filter(date__gte=timezone.localdate())[:10],
    })


MODE_COLOURS = {"studio": "#111212", "online": "#0081F6", "site_visit": "#12A06A"}


@team_required
@require_GET
def bookings_events(request):
    def parse(v):
        try:
            return datetime.fromisoformat((v or "")[:10]).date()
        except ValueError:
            return None
    start = parse(request.GET.get("start")) or timezone.localdate() - timedelta(days=7)
    end = parse(request.GET.get("end")) or start + timedelta(days=42)
    events = []
    for b in Booking.objects.filter(date__gte=start, date__lt=end).select_related("lead"):
        cancelled = b.status == Booking.Status.CANCELLED
        events.append({
            "id": b.pk,
            "title": f"{b.name} · {b.get_mode_display()}",
            "start": timezone.localtime(b.start).isoformat(),
            "end": timezone.localtime(b.end).isoformat(),
            "color": "#C9CED6" if cancelled else MODE_COLOURS.get(b.mode, "#2B2622"),
            "editable": not cancelled,
            "extendedProps": {
                "reference": b.reference, "name": b.name, "mobile": b.mobile, "mode": b.get_mode_display(),
                "status": b.status, "statusLabel": b.get_status_display(), "notes": b.notes,
                "address": b.site_address, "leadUrl": reverse("studio:lead_detail", args=[b.lead_id]) if b.lead_id else "",
                "when": f"{b.date:%a, %d-%m-%Y} · {b.start_time:%I:%M %p}",
            },
        })
    for blk in BlockedDate.objects.filter(date__gte=start, date__lt=end):
        events.append({"start": blk.date.isoformat(), "allDay": True, "display": "background",
                       "color": "rgba(0,129,246,.08)", "title": blk.reason or "Blocked"})
    return JsonResponse(events, safe=False)


@team_required
@require_POST
def booking_move(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    data = _json_body(request) or {}
    try:
        new_start = timezone.localtime(datetime.fromisoformat(data["start"]))
    except (KeyError, ValueError, TypeError):
        return HttpResponseBadRequest("Invalid date")
    if timezone.is_naive(new_start):
        new_start = timezone.make_aware(new_start)
    if new_start < timezone.now() - timedelta(minutes=5):
        return JsonResponse({"ok": False, "error": "You can’t move a booking into the past."}, status=400)
    clash = (Booking.objects.filter(date=new_start.date(), start_time=new_start.time().replace(second=0, microsecond=0))
             .exclude(status=Booking.Status.CANCELLED).exclude(pk=booking.pk).exists())
    if clash:
        return JsonResponse({"ok": False, "error": "Another booking is already in that slot."}, status=409)
    old = f"{booking.date:%d-%m-%Y} {booking.start_time:%I:%M %p}"
    booking.date, booking.start_time = new_start.date(), new_start.time().replace(second=0, microsecond=0)
    try:
        with transaction.atomic():
            booking.save(update_fields=["date", "start_time"])
    except IntegrityError:
        return JsonResponse({"ok": False, "error": "Another booking is already in that slot."}, status=409)
    if booking.lead_id:
        LeadActivity.objects.create(lead_id=booking.lead_id, user=request.user,
                                    text=f"Rescheduled {booking.reference} from {old} to "
                                         f"{booking.date:%d-%m-%Y} {booking.start_time:%I:%M %p}")
    return JsonResponse({"ok": True, "when": f"{booking.date:%a, %d-%m-%Y} · {booking.start_time:%I:%M %p}"})


@team_required
@require_POST
def booking_status(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    status = request.POST.get("status")
    if status not in Booking.Status.values:
        return HttpResponseBadRequest("Invalid status")
    booking.status = status
    booking.save(update_fields=["status"])
    if booking.lead_id:
        LeadActivity.objects.create(lead_id=booking.lead_id, user=request.user,
                                    text=f"Booking {booking.reference} marked {booking.get_status_display().lower()}")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "label": booking.get_status_display()})
    messages.success(request, f"Booking {booking.reference} marked {booking.get_status_display().lower()}.")
    return redirect("studio:bookings")


@owner_required
def availability(request):
    formset = AvailabilityFormSet(request.POST or None, queryset=WeeklyAvailability.objects.all(), prefix="av")
    block_form = BlockedDateForm(prefix="blk")
    if request.method == "POST":
        if "add_block" in request.POST:
            block_form = BlockedDateForm(request.POST, prefix="blk")
            if block_form.is_valid():
                block_form.save()
                messages.success(request, "Date blocked. It no longer shows on the booking page.")
                return redirect("studio:availability")
            formset = AvailabilityFormSet(queryset=WeeklyAvailability.objects.all(), prefix="av")
        elif formset.is_valid():
            formset.save()
            messages.success(request, "Weekly availability saved. The public booking page is updated.")
            return redirect("studio:availability")
        else:
            messages.error(request, "Please fix the highlighted rows.")
    return render(request, "studio/availability.html", {
        "formset": formset, "block_form": block_form,
        "blocked": BlockedDate.objects.filter(date__gte=timezone.localdate()),
    })


@owner_required
@require_POST
def unblock_date(request, pk):
    get_object_or_404(BlockedDate, pk=pk).delete()
    messages.success(request, "Date unblocked.")
    return redirect("studio:availability")


# ===================================================================== projects
@team_required
def projects(request):
    view = request.GET.get("view", "board")
    qs = (ClientProject.objects.select_related("designer")
          .prefetch_related("milestones")
          .annotate(open_tasks=Count("tasks", filter=~Q(tasks__status=Task.Status.DONE))))
    columns = [{"value": v, "label": l, "projects": [p for p in qs if p.stage == v]}
               for v, l in ClientProject.Stage.choices]
    return render(request, "studio/projects.html", {"projects": qs, "columns": columns, "view": view})


@team_required
@require_POST
def project_move(request):
    data = _json_body(request) or {}
    project = get_object_or_404(ClientProject, pk=data.get("project"))
    stage = data.get("stage")
    if stage not in ClientProject.Stage.values:
        return HttpResponseBadRequest("Invalid stage")
    project.stage = stage
    project.save(update_fields=["stage", "updated_at"])
    for i, pk in enumerate(data.get("order", [])[:500]):
        ClientProject.objects.filter(pk=pk, stage=stage).update(position=i)
    return JsonResponse({"ok": True, "stage_label": project.get_stage_display()})


@owner_required
def project_create(request):
    form = ProjectForm(request.POST or None, initial={"designer": request.user})
    if request.method == "POST" and form.is_valid():
        project = form.save()
        for i, title in enumerate(["Design & 3D", "Design approval", "Material ordering", "Execution", "Handover"]):
            Milestone.objects.create(project=project, title=title, order=i)
        messages.success(request, f"Project {project.code} created.")
        return redirect(project.get_absolute_url())
    return render(request, "studio/project_form.html", {"form": form})


@team_required
def project_detail(request, pk):
    project = get_object_or_404(ClientProject.objects.select_related("designer", "client", "lead"), pk=pk)
    tab = request.GET.get("tab", "overview")
    tabs = [("overview", "Overview", 0),
            ("tasks", "Tasks", project.tasks.exclude(status=Task.Status.DONE).count()),
            ("designs", "Designs", project.proposals.count()),
            ("updates", "Site updates", project.updates.count()),
            ("documents", "Documents", project.documents.count()),
            ("billing", "Billing", project.invoices.exclude(status="cancelled").filter(status__in=["issued", "partial"]).count())]
    if tab not in {t[0] for t in tabs}:
        tab = "overview"
    return render(request, "studio/project_detail.html", {
        "project": project, "tab": tab, "tabs": tabs, "milestone_statuses": Milestone.Status.choices,
        "tasks": project.tasks.select_related("assigned_to"),
        "milestones": project.milestones.all(),
        "spaces": project.spaces.all(),
        "proposals": project.proposals.prefetch_related("images", "comments__author", "comments__image"),
        "updates": project.updates.prefetch_related("photos").select_related("author"),
        "documents": project.documents.all(),
        "requests": project.requests.select_related("task"),
        "task_form": TaskForm(initial={"assigned_to": project.designer_id}),
        "milestone_form": MilestoneForm(), "space_form": SpaceForm(),
        "proposal_form": ProposalForm(), "update_form": SiteUpdateForm(), "document_form": DocumentForm(),
        "edit_form": ProjectForm(instance=project) if is_owner(request.user) else None,
        "quotations": project.quotations.all(),
        "schedule": project.schedule.prefetch_related("invoices__payments"),
        "invoices": project.invoices.prefetch_related("payments"),
        "billing": _billing_summary(project),
        "today": timezone.localdate(),
    })


def _billing_summary(project):
    from finance.models import Invoice
    invoices = [i for i in project.invoices.prefetch_related("payments") if i.status != Invoice.Status.CANCELLED]
    accepted = project.quotations.filter(status="accepted").first()
    received = sum((i.paid for i in invoices), 0)
    return {"contract": accepted.grand_total if accepted else 0, "invoiced": sum((i.total for i in invoices), 0),
            "received": received, "outstanding": sum((i.balance for i in invoices), 0),
            "pct": round(100 * float(received) / float(accepted.grand_total)) if accepted and accepted.grand_total else 0}


def _back(project, tab):
    return redirect(f"{project.get_absolute_url()}?tab={tab}")


@owner_required
@require_POST
def project_edit(request, pk):
    project = get_object_or_404(ClientProject, pk=pk)
    form = ProjectForm(request.POST, instance=project)
    if form.is_valid():
        form.save()
        messages.success(request, "Project details saved.")
    else:
        messages.error(request, "Could not save: " + "; ".join(f"{k}: {v[0]}" for k, v in form.errors.items()))
    return _back(project, "overview")


@team_required
@require_POST
def task_add(request, pk):
    project = get_object_or_404(ClientProject, pk=pk)
    form = TaskForm(request.POST)
    if form.is_valid():
        task = form.save(commit=False)
        task.project, task.created_by = project, request.user
        task.save()
        messages.success(request, "Task added.")
    else:
        messages.error(request, "Please give the task a title.")
    return _back(project, request.POST.get("tab", "tasks"))


@team_required
@require_POST
def task_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    status = request.POST.get("status")
    if status not in Task.Status.values:
        return HttpResponseBadRequest("Invalid status")
    task.status = status
    task.completed_at = timezone.now() if status == Task.Status.DONE else None
    task.save(update_fields=["status", "completed_at"])
    req = getattr(task, "client_request", None)
    if req:
        req.status = {"done": "resolved", "doing": "in_progress"}.get(status, "open")
        req.save(update_fields=["status"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "label": task.get_status_display()})
    return redirect(request.POST.get("next") or f"{task.project.get_absolute_url()}?tab=tasks")


@team_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    project = task.project
    task.delete()
    messages.success(request, "Task deleted.")
    return _back(project, "tasks")


@team_required
def my_tasks(request):
    show = request.GET.get("show", "mine")
    tasks = Task.objects.exclude(status=Task.Status.DONE).select_related("project", "assigned_to")
    if show == "mine":
        tasks = tasks.filter(assigned_to=request.user)
    return render(request, "studio/tasks.html", {"tasks": tasks, "show": show, "today": timezone.localdate()})


@team_required
@require_POST
def milestone_add(request, pk):
    project = get_object_or_404(ClientProject, pk=pk)
    form = MilestoneForm(request.POST)
    if form.is_valid():
        m = form.save(commit=False)
        m.project, m.order = project, project.milestones.count()
        m.save()
        messages.success(request, "Milestone added.")
    return _back(project, "overview")


@team_required
@require_POST
def milestone_status(request, pk):
    m = get_object_or_404(Milestone, pk=pk)
    status = request.POST.get("status")
    if status in Milestone.Status.values:
        m.status = status
        m.completed_on = timezone.localdate() if status == Milestone.Status.DONE else None
        m.save(update_fields=["status", "completed_on"])
        messages.success(request, f"“{m.title}” marked {m.get_status_display().lower()}.")
    return _back(m.project, "overview")


@team_required
@require_POST
def space_add(request, pk):
    project = get_object_or_404(ClientProject, pk=pk)
    form = SpaceForm(request.POST)
    if form.is_valid():
        s = form.save(commit=False)
        s.project, s.order = project, project.spaces.count()
        s.save()
        messages.success(request, "Room added.")
    return _back(project, "overview")


@team_required
@require_POST
def space_delete(request, pk):
    s = get_object_or_404(ProjectSpace, pk=pk)
    project = s.project
    s.delete()
    return _back(project, "overview")


@team_required
@require_POST
def proposal_add(request, pk):
    project = get_object_or_404(ClientProject, pk=pk)
    form = ProposalForm(request.POST, request.FILES)
    if form.is_valid():
        with transaction.atomic():
            p = form.save(commit=False)
            p.project, p.created_by = project, request.user
            p.version = (project.proposals.order_by("-version").values_list("version", flat=True).first() or 0) + 1
            if form.cleaned_data["share"]:
                p.status, p.shared_at = DesignProposal.Status.SHARED, timezone.now()
            p.save()
            for i, f in enumerate(form.cleaned_data["images"]):
                ProposalImage.objects.create(proposal=p, image=f, order=i)
        messages.success(request, f"Design v{p.version} uploaded" + (" and shared with the client." if p.shared_at else "."))
    else:
        messages.error(request, "Could not upload: " + "; ".join(str(e[0]) for e in form.errors.values()))
    return _back(project, "designs")


@team_required
@require_POST
def proposal_share(request, pk):
    p = get_object_or_404(DesignProposal, pk=pk)
    if p.status == DesignProposal.Status.DRAFT:
        p.status, p.shared_at = DesignProposal.Status.SHARED, timezone.now()
        p.save(update_fields=["status", "shared_at"])
        messages.success(request, f"Design v{p.version} shared with the client.")
    return _back(p.project, "designs")


@team_required
@require_POST
def update_add(request, pk):
    project = get_object_or_404(ClientProject, pk=pk)
    form = SiteUpdateForm(request.POST, request.FILES)
    if form.is_valid():
        with transaction.atomic():
            u = SiteUpdate.objects.create(project=project, author=request.user, message=form.cleaned_data["message"])
            for f in form.cleaned_data["photos"]:
                SiteUpdatePhoto.objects.create(update=u, image=f)
        messages.success(request, "Update posted to the client portal.")
    else:
        messages.error(request, "Could not post: " + "; ".join(str(e[0]) for e in form.errors.values()))
    return _back(project, "updates")


@team_required
@require_POST
def document_add(request, pk):
    project = get_object_or_404(ClientProject, pk=pk)
    form = DocumentForm(request.POST, request.FILES)
    if form.is_valid():
        d = form.save(commit=False)
        d.project, d.uploaded_by = project, request.user
        d.save()
        messages.success(request, "Document uploaded.")
    else:
        messages.error(request, "Could not upload: " + "; ".join(str(e[0]) for e in form.errors.values()))
    return _back(project, "documents")


@team_required
@require_POST
def document_delete(request, pk):
    d = get_object_or_404(ProjectDocument, pk=pk)
    project = d.project
    d.file.delete(save=False)
    d.delete()
    messages.success(request, "Document deleted.")
    return _back(project, "documents")


# ===================================================================== studio settings
@owner_required
def studio_settings(request):
    from core.models import StudioSettings

    from .forms import StudioSettingsForm
    settings_obj = StudioSettings.load()
    form = StudioSettingsForm(request.POST or None, request.FILES or None, instance=settings_obj)
    # Extra features are switched on by DEVNIXPLUS only (superuser); the studio sees their status and can request them.
    if not request.user.is_superuser:
        form.fields.pop("module_tour360", None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Studio settings saved. The website and documents now use them.")
            return redirect("studio:settings")
        messages.error(request, "Please fix the highlighted fields.")
    sections = [
        ("brand", "Brand", "palette", ["name", "tagline", "logo", "accent_color", "secondary_color", "dark_color"]),
        ("contact", "Contact", "telephone", ["city", "address", "phone", "whatsapp", "email", "map_embed_query",
                                             "instagram", "working_hours", "founded_year"]),
        ("website", "Website text", "window", ["hero_title", "hero_subtitle", "about_text"]),
        ("billing", "GST & payments", "receipt", ["legal_name", "gstin", "state_name", "default_gst_percent",
                                                 "schedule_text", "quotation_terms", "bank_details", "easy_payment_text"]),
        ("rates", "Estimator rates", "calculator", ["rate_essential", "rate_premium", "rate_luxury"]),
        ("modules", "Modules", "toggles", ["module_website", "module_cms", "module_portal", "module_erp",
                                           "module_automation", "module_ai", "show_locked_teasers"]
         + (["module_tour360"] if "module_tour360" in form.fields else [])),
    ]
    from core.modules import EXTRA_FEATURES, extra_status
    extras = [{"key": k, "label": f["label"], "icon": f["icon"], "status": extra_status(k, settings_obj),
               "url": reverse(f["manage_url"])} for k, f in EXTRA_FEATURES.items()]
    return render(request, "studio/settings.html", {
        "form": form, "extras": extras,
        "sections": [(key, label, icon, [form[f] for f in fields]) for key, label, icon, fields in sections],
        "error_sections": {key for key, _, _, fields in sections if any(form[f].errors for f in fields)},
    })


# ===================================================================== live client activity
@team_required
def client_activity(request):
    """Polled by the studio pages: client approvals, change requests, comments and requests since `since`."""
    from django.utils.dateparse import parse_datetime

    from .client_actions import client_events
    since = parse_datetime(request.GET.get("since", "") or "")
    now = timezone.now()
    if since is None or timezone.is_naive(since) or since < now - timedelta(days=1):
        since = now - timedelta(seconds=60)
    events = client_events(since)[:10]
    from core.models import StudioSettings
    if StudioSettings.load().module_automation:
        from automations.models import AutomationLog
        for log in AutomationLog.objects.filter(created_at__gt=since)[:5]:
            who = "you" if log.to_owner else log.recipient_name
            events.append({"text": f"WhatsApp ready: {log.get_automation_display()} → {who}",
                           "url": reverse("automations:index") + "#log", "kind": "automation", "at": log.created_at})
        events.sort(key=lambda e: e["at"], reverse=True)
    return JsonResponse({"now": now.isoformat(), "events": [
        {"text": e["text"], "url": e["url"], "kind": e["kind"], "at": e["at"].isoformat()} for e in events]})


# ===================================================================== team & roles (basic)
ROLE_MATRIX = [
    ("Leads, bookings & calendar", True, True),
    ("Projects, tasks, designs & site updates", True, True),
    ("Quotations & invoices (create, send)", True, True),
    ("Convert a lead into a project", True, False),
    ("Studio settings, availability & modules", True, False),
    ("Automation messages & AI knowledge base (edit)", True, False),
    ("Team & roles", True, False),
]


@owner_required
def team(request):
    from django.contrib.auth.models import Group, User

    from core import locked
    from core.permissions import OWNER, TEAM

    from .forms import TeamMemberForm
    form = TeamMemberForm(request.POST or None)
    if request.method == "POST" and request.POST.get("action") == "add":
        if form.is_valid():
            d = form.cleaned_data
            u = User.objects.create_user(d["username"], d["email"], d["password"],
                                         first_name=d["first_name"], last_name=d["last_name"])
            u.groups.add(Group.objects.get_or_create(name=d["role"])[0])
            messages.success(request, f"{u.get_full_name() or u.username} can now sign in as “{u.username}”.")
            return redirect("studio:team")
    elif request.method == "POST" and request.POST.get("action") == "toggle":
        u = get_object_or_404(User.objects.filter(groups__name__in=[OWNER, TEAM]).distinct(), pk=request.POST.get("user"))
        if u == request.user:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            u.is_active = not u.is_active
            u.save(update_fields=["is_active"])
            messages.success(request, f"{u.get_full_name() or u.username} {'reactivated' if u.is_active else 'deactivated'}.")
        return redirect("studio:team")
    ids = User.objects.filter(groups__name__in=[OWNER, TEAM]).values("pk")
    members = list(User.objects.filter(pk__in=ids).prefetch_related("groups")
                   .annotate(open_tasks=Count("tasks", filter=~Q(tasks__status=Task.Status.DONE)))
                   .order_by("-is_active", "first_name"))
    for m in members:
        m.role_label = "Owner" if (m.is_superuser or any(g.name == OWNER for g in m.groups.all())) else "Team member"
    return render(request, "studio/team.html", {
        "form": form, "members": members, "matrix": ROLE_MATRIX, "show_form": request.method == "POST",
        "locked_roles": locked.get("roles_branches"), "locked_payroll": locked.get("team_payroll"),
    })


# ===================================================================== reports (basic)
@team_required
def reports(request):
    from . import reports as R
    months = request.GET.get("months", "6")
    if months not in dict(R.PERIODS):
        months = "6"
    m = int(months)
    start = R.period_start(m)
    rows = R.outstanding()
    revenue = metrics.revenue_by_month(m)
    sources = R.source_rows(start)
    return render(request, "studio/reports.html", {
        "months": months, "periods": R.PERIODS, "start": start, "summary": R.summary(start),
        "sources": sources, "revenue": revenue, "revenue_total": sum(a for _, a in revenue),
        "outstanding": rows, "outstanding_total": sum((r["balance"] for r in rows), 0),
        "overdue_total": sum((r["balance"] for r in rows if r["days_overdue"]), 0),
        "ageing": R.ageing(rows), "payments": R.payments(start)[:10],
        "chart": {"sources": [(r["source"], r["leads"], r["won"]) for r in sources], "revenue": revenue},
    })


@team_required
def report_csv(request, kind):
    from django.http import Http404

    from . import reports as R
    months = request.GET.get("months", "6")
    resp = R.csv_export(kind, int(months) if months in dict(R.PERIODS) else 6)
    if resp is None:
        raise Http404
    return resp
