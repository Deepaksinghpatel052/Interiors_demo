import json
import uuid

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import StudioSettings
from core.permissions import is_owner, owner_required, team_required
from core.ratelimit import client_ip, hit
from crm.models import Lead, LeadActivity
from website.forms import clean_indian_mobile

from . import llm, rag
from .models import ChatMessage, ChatSession, KnowledgeDocument


def _json(request):
    try:
        data = json.loads(request.body or "{}")
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _session(key, channel, user=None):
    try:
        key = uuid.UUID(str(key))
    except (TypeError, ValueError):
        key = None
    session = ChatSession.objects.filter(key=key, channel=channel).first() if key else None
    if session is None:
        session = ChatSession.objects.create(channel=channel, user=user if getattr(user, "is_authenticated", False) else None)
    return session


def _history(session):
    return [{"role": m.role, "text": m.text} for m in session.messages.order_by("-created_at")[:llm.HISTORY_TURNS]][::-1]


def _payload(session, ans, **extra):
    return {"session": str(session.key), "html": ans.html, "sources": ans.sources, "projects": ans.projects,
            "mode": ans.mode, **extra}


# ============================================================================ public Design Assistant
def _capture_lead(session, name, mobile, user_text):
    """Create (or reuse) a lead with source = AI assistant and attach the chat."""
    lead = session.lead or Lead.objects.filter(mobile=mobile).exclude(stage__in=["won", "lost"]).first()
    transcript = "\n".join(f"{'Visitor' if m.role == 'user' else 'Assistant'}: {m.text}"
                           for m in session.messages.all()[:20])
    if lead is None:
        lead = Lead.objects.create(name=name or "Website visitor (AI chat)", mobile=mobile, source=Lead.Source.AI,
                                   message=f"From the AI Design Assistant chat:\n{transcript}"[:4000])
        LeadActivity.objects.create(lead=lead, text="New lead from the AI Design Assistant (chat saved)")
    else:
        if name and lead.name.startswith("Website visitor"):
            lead.name = name
            lead.save(update_fields=["name", "updated_at"])
        LeadActivity.objects.create(lead=lead, text="Chatted with the AI Design Assistant")
    session.lead = lead
    session.save(update_fields=["lead", "last_at"])
    return lead


@require_POST
def public_chat(request):
    if not StudioSettings.load().module_ai:
        raise Http404
    data = _json(request)
    text = str(data.get("message", "")).strip()
    if not text:
        return JsonResponse({"error": "Please type a question."}, status=400)
    if len(text) > settings.AI_MAX_MESSAGE_CHARS:
        return JsonResponse({"error": f"Please keep your question under {settings.AI_MAX_MESSAGE_CHARS} characters."}, status=400)
    session = _session(data.get("session"), ChatSession.Channel.PUBLIC, request.user)
    limit, window = settings.AI_PUBLIC_LIMIT
    ip_limit, ip_window = settings.AI_IP_LIMIT
    if not hit(f"chat:s:{session.key}", limit, window) or not hit(f"chat:ip:{client_ip(request)}", ip_limit, ip_window):
        return JsonResponse({"error": "You're sending messages quickly — please wait a few minutes, or message us on WhatsApp.",
                             "session": str(session.key)}, status=429)

    history = _history(session)
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, text=text)
    contact = llm.extract_contact(text)
    lead_captured = False
    if contact:
        name, mobile = contact
        _capture_lead(session, name, mobile, text)
        lead_captured = True
        thanks = f"Thank you{', ' + name if name else ''}! Our designer will call you on {mobile} within one working day."
        ans = llm.answer(text, "public", history) if len(text) > 40 else llm.Answer(text=thanks, mode="lead")
        if ans.mode != "lead":
            ans.text = thanks + "\n\n" + ans.text
    else:
        ans = llm.answer(text, "public", history)
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.ASSISTANT, text=ans.text,
                               sources=ans.sources, mode=ans.mode)
    return JsonResponse(_payload(session, ans, lead=lead_captured))


@require_POST
def public_lead(request):
    if not StudioSettings.load().module_ai:
        raise Http404
    data = _json(request)
    name = str(data.get("name", "")).strip()[:100]
    try:
        mobile = clean_indian_mobile(str(data.get("mobile", "")))
    except ValidationError:
        return JsonResponse({"error": "Please enter a valid 10-digit mobile number."}, status=400)
    if len(name) < 2:
        return JsonResponse({"error": "Please enter your name."}, status=400)
    if not hit(f"chatlead:ip:{client_ip(request)}", 5, 3600):
        return JsonResponse({"error": "Too many requests. Please try again later."}, status=429)
    session = _session(data.get("session"), ChatSession.Channel.PUBLIC, request.user)
    _capture_lead(session, name, mobile, "")
    return JsonResponse({"ok": True, "message": f"Thank you, {name}! Our designer will call you on {mobile} soon.",
                         "session": str(session.key)})


# ============================================================================ internal Studio Assistant
@team_required
def studio_assistant(request):
    recent = ChatSession.objects.filter(channel=ChatSession.Channel.INTERNAL, user=request.user)[:5]
    return render(request, "assistant/studio_chat.html", {
        "recent": recent, "ai_mock": settings.AI_MOCK,
        "examples": ["What should I check before handover?", "What are the payment terms with Mehta Laminates?",
                     "How much discount can I give without approval?", "What do I carry for a site visit?"]})


@team_required
@require_POST
def studio_ask(request):
    data = _json(request)
    text = str(data.get("message", "")).strip()[:1000]
    if not text:
        return JsonResponse({"error": "Please type a question."}, status=400)
    if not hit(f"chat:u:{request.user.pk}", 60, 3600):
        return JsonResponse({"error": "Too many questions this hour. Please try again later."}, status=429)
    session = _session(data.get("session"), ChatSession.Channel.INTERNAL, request.user)
    history = _history(session)
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, text=text)
    ans = llm.answer(text, "internal", history)
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.ASSISTANT, text=ans.text, sources=ans.sources, mode=ans.mode)
    return JsonResponse(_payload(session, ans))


# ============================================================================ knowledge base
class KnowledgeForm(forms.ModelForm):
    class Meta:
        model = KnowledgeDocument
        fields = ["title", "doc_type", "audience", "content", "file", "url", "is_active"]
        widgets = {"content": forms.Textarea(attrs={"rows": 10}),
                   "file": forms.ClearableFileInput(attrs={"accept": ".pdf,.txt"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doc_type"].choices = [c for c in KnowledgeDocument.DocType.choices if c[0] != "portfolio"]
        for name, f in self.fields.items():
            css = "form-check-input" if name == "is_active" else ("form-select" if isinstance(f.widget, forms.Select) else "form-control")
            f.widget.attrs.setdefault("class", css)

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f and hasattr(f, "name") and not f.name.lower().endswith((".pdf", ".txt")):
            raise ValidationError("Upload a PDF or TXT file.")
        return f

    def clean(self):
        d = super().clean()
        if not (d.get("content") or "").strip() and not d.get("file"):
            raise ValidationError("Add some text or upload a PDF/TXT file.")
        return d


@team_required
def kb_list(request):
    q, audience, doc_type = request.GET.get("q", "").strip(), request.GET.get("audience", ""), request.GET.get("type", "")
    docs = KnowledgeDocument.objects.annotate(chunk_count=Count("chunks")).order_by("audience", "doc_type", "title")
    if q:
        docs = docs.filter(Q(title__icontains=q) | Q(content__icontains=q))
    if audience in KnowledgeDocument.Audience.values:
        docs = docs.filter(audience=audience)
    if doc_type in KnowledgeDocument.DocType.values:
        docs = docs.filter(doc_type=doc_type)
    form = KnowledgeForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if not is_owner(request.user):
            raise Http404
        if form.is_valid():
            doc = form.save()
            messages.success(request, f"“{doc.title}” added and indexed ({doc.chunks.count()} chunks).")
            return redirect("assistant:kb")
        messages.error(request, "Please fix the document details.")
    page = Paginator(docs, 30).get_page(request.GET.get("page"))
    return render(request, "assistant/kb.html", {
        "page": page, "form": form, "q": q, "audience": audience, "doc_type": doc_type,
        "audiences": KnowledgeDocument.Audience.choices, "types": KnowledgeDocument.DocType.choices,
        "total": KnowledgeDocument.objects.count(),
        "chunks_total": sum(d.chunk_count for d in KnowledgeDocument.objects.annotate(chunk_count=Count("chunks"))),
        "ai_mock": settings.AI_MOCK, "model": settings.ANTHROPIC_MODEL})


@owner_required
def kb_edit(request, pk):
    doc = get_object_or_404(KnowledgeDocument, pk=pk)
    if doc.is_synced:
        messages.info(request, "This document is synced from the website. Edit the FAQ, service or project instead.")
        return redirect("assistant:kb")
    form = KnowledgeForm(request.POST or None, request.FILES or None, instance=doc)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Document saved and re-indexed.")
        return redirect("assistant:kb")
    return render(request, "assistant/kb_form.html", {"form": form, "doc": doc,
                                                      "chunks": doc.chunks.all()[:20]})


@owner_required
@require_POST
def kb_delete(request, pk):
    doc = get_object_or_404(KnowledgeDocument, pk=pk, source_key__isnull=True)
    doc.delete()
    messages.success(request, "Document removed from the knowledge base.")
    return redirect("assistant:kb")


@owner_required
@require_POST
def kb_reindex(request):
    from .sync import sync_all
    sync_all()
    n = rag.reindex_all()
    messages.success(request, f"Re-indexed {n} documents.")
    return redirect("assistant:kb")


@team_required
@require_POST
def kb_test(request):
    """'Test the assistant': shows the retrieved chunks next to the answer (great for explaining RAG)."""
    data = _json(request)
    text = str(data.get("message", "")).strip()[:1000]
    audience = "internal" if data.get("audience") == "internal" else "public"
    if not text:
        return JsonResponse({"error": "Type a question to test."}, status=400)
    if not hit(f"kbtest:u:{request.user.pk}", 60, 3600):
        return JsonResponse({"error": "Too many tests this hour."}, status=429)
    ans = llm.answer(text, audience)
    return JsonResponse({
        "html": ans.html, "sources": ans.sources, "mode": ans.mode, "note": ans.note, "projects": ans.projects,
        "hits": [{"n": i + 1, "title": h.document.title, "audience": h.document.audience, "score": round(h.score, 2),
                  "text": h.chunk.text} for i, h in enumerate(ans.hits)]})


# ============================================================================ chat logs
@owner_required
def chat_logs(request):
    channel = request.GET.get("channel", "")
    sessions = (ChatSession.objects.annotate(n=Count("messages")).filter(n__gt=0)
                .select_related("lead", "user").order_by("-last_at"))
    if channel in ChatSession.Channel.values:
        sessions = sessions.filter(channel=channel)
    page = Paginator(sessions, 25).get_page(request.GET.get("page"))
    for s in page:
        s.first_question = s.messages.filter(role="user").first()
    return render(request, "assistant/chats.html", {"page": page, "channel": channel,
                                                    "leads_from_ai": Lead.objects.filter(source=Lead.Source.AI).count()})


@owner_required
def chat_detail(request, pk):
    session = get_object_or_404(ChatSession.objects.select_related("lead", "user"), pk=pk)
    return render(request, "assistant/chat_detail.html", {"session": session, "chat": session.messages.all()})
