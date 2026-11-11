from django.contrib import admin

from .models import ChatMessage, ChatSession, KnowledgeChunk, KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "doc_type", "audience", "is_active", "updated_at"]
    list_filter = ["audience", "doc_type", "is_active"]
    search_fields = ["title", "content"]


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ["role", "text", "sources", "mode", "created_at"]


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ["key", "channel", "lead", "user", "last_at"]
    list_filter = ["channel"]
    inlines = [ChatMessageInline]


admin.site.register(KnowledgeChunk)
