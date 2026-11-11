from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    # public website
    path("api/chat/", views.public_chat, name="public_chat"),
    path("api/chat/lead/", views.public_lead, name="public_lead"),
    # studio
    path("studio/assistant/", views.studio_assistant, name="studio"),
    path("studio/assistant/ask/", views.studio_ask, name="studio_ask"),
    path("studio/ai/", views.kb_list, name="kb"),
    path("studio/ai/test/", views.kb_test, name="kb_test"),
    path("studio/ai/reindex/", views.kb_reindex, name="kb_reindex"),
    path("studio/ai/<int:pk>/", views.kb_edit, name="kb_edit"),
    path("studio/ai/<int:pk>/delete/", views.kb_delete, name="kb_delete"),
    path("studio/ai/chats/", views.chat_logs, name="chats"),
    path("studio/ai/chats/<int:pk>/", views.chat_detail, name="chat_detail"),
]
