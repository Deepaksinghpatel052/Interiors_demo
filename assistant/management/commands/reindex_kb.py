from django.core.management.base import BaseCommand

from assistant import rag
from assistant.sync import sync_all


class Command(BaseCommand):
    help = "Re-sync FAQs, services and portfolio into the knowledge base and rebuild every chunk + BM25 index."

    def handle(self, *args, **opts):
        sync_all()
        n = rag.reindex_all()
        self.stdout.write(self.style.SUCCESS(f"Re-indexed {n} knowledge documents."))
