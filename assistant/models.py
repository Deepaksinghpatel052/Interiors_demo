import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse

from core.validators import validate_document


class KnowledgeDocument(models.Model):
    class DocType(models.TextChoices):
        FAQ = "faq", "FAQ"
        SERVICE = "service", "Service"
        PROCESS = "process", "Process"
        POLICY = "policy", "Policy"
        MATERIAL = "material", "Material guide"
        PORTFOLIO = "portfolio", "Portfolio project"
        UPLOAD = "upload", "Uploaded file"

    class Audience(models.TextChoices):
        PUBLIC = "public", "Public (website assistant)"
        INTERNAL = "internal", "Internal (studio team only)"

    title = models.CharField(max_length=160)
    doc_type = models.CharField("Type", max_length=20, choices=DocType.choices, default=DocType.POLICY)
    audience = models.CharField(max_length=10, choices=Audience.choices, default=Audience.PUBLIC)
    content = models.TextField(blank=True, help_text="Plain text. Leave empty when uploading a PDF/TXT file.")
    file = models.FileField(upload_to="knowledge/", blank=True, validators=[validate_document],
                            help_text="Optional PDF or TXT. Its text is extracted into the knowledge base.")
    source_key = models.CharField(max_length=60, unique=True, null=True, blank=True, editable=False,
                                  help_text="Set for documents synced automatically from FAQs, services and portfolio.")
    url = models.CharField(max_length=200, blank=True, help_text="Page to link from answers, e.g. /portfolio/…")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["audience", "doc_type", "title"]

    def __str__(self):
        return self.title

    @property
    def is_synced(self):
        return bool(self.source_key)


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(KnowledgeDocument, related_name="chunks", on_delete=models.CASCADE)
    index = models.PositiveIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["document", "index"]


class ChatSession(models.Model):
    class Channel(models.TextChoices):
        PUBLIC = "public", "Website Design Assistant"
        INTERNAL = "internal", "Studio Assistant"

    key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.PUBLIC)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    lead = models.ForeignKey("crm.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="chats")
    created_at = models.DateTimeField(auto_now_add=True)
    last_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_at"]

    def __str__(self):
        return f"{self.get_channel_display()} · {self.created_at:%d-%m-%Y %H:%M}"

    def get_absolute_url(self):
        return reverse("assistant:chat_detail", args=[self.pk])


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Visitor"
        ASSISTANT = "assistant", "Assistant"

    session = models.ForeignKey(ChatSession, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices)
    text = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    mode = models.CharField(max_length=10, blank=True, help_text="mock / claude / fallback")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
