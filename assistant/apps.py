from django.apps import AppConfig


class AssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assistant"
    verbose_name = "AI assistant"

    def ready(self):
        from . import sync  # noqa: F401  (registers the knowledge-base sync signals)
