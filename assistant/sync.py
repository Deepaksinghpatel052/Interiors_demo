"""Keep the knowledge base in step with the website: FAQs, services and portfolio projects are
copied into KnowledgeDocuments (and re-indexed) whenever they are saved or deleted."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from website.models import FAQ, PortfolioProject, ProjectRoom, ProjectSwatch, Service

from . import rag
from .models import KnowledgeDocument


def _upsert(key, *, title, doc_type, content, url="", active=True):
    doc, _ = KnowledgeDocument.objects.update_or_create(
        source_key=key,
        defaults={"title": title[:160], "doc_type": doc_type, "audience": KnowledgeDocument.Audience.PUBLIC,
                  "content": content, "url": url, "is_active": active})
    rag.index_document(doc)
    return doc


def _remove(key):
    KnowledgeDocument.objects.filter(source_key=key).delete()
    rag.bump_version()


def sync_faq(faq):
    return _upsert(f"faq:{faq.pk}", title=f"FAQ: {faq.question}", doc_type="faq", url="/faq/",
                   content=faq.answer, active=faq.is_active)


def sync_service(s):
    includes = "\n".join(f"- {line.strip()}" for line in s.includes.splitlines() if line.strip())
    return _upsert(f"service:{s.pk}", title=f"Service: {s.title}", doc_type="service", url=f"/services/#{s.slug}",
                   content=f"{s.title}. {s.short}\n\n{s.description}\n\nWhat's included:\n{includes}\n\n"
                           f"Typical timeline: {s.typical_timeline or 'shared after the consultation'}.",
                   active=s.is_active)


def sync_project(p):
    rooms = "\n".join(f"- {r.name}: {r.description}" for r in p.rooms.all())
    materials = ", ".join(f"{m.name} ({m.note})" if m.note else m.name for m in p.materials)
    colours = ", ".join(c.name for c in p.colours)
    prop = ", " + p.get_property_type_display() if p.property_type else ""
    parts = [
        f"Portfolio project: {p.title}, {p.location}. Style: {p.get_style_display()}. "
        f"Space: {p.get_room_type_display()}{prop}. Budget band: {p.get_budget_band_display()}. "
        f"Area: {p.area_sqft} sq ft. Completed in {p.duration_weeks} weeks.",
        p.summary,
        "Brief: " + p.brief if p.brief else "",
        p.description,
        "Rooms:\n" + rooms if rooms else "",
        " ".join(x for x in ["Materials: " + materials + "." if materials else "",
                             "Colour palette: " + colours + "." if colours else ""] if x),
    ]
    content = "\n\n".join(x for x in parts if x)
    return _upsert(f"project:{p.pk}", title=f"Project: {p.title}", doc_type="portfolio", url=p.get_absolute_url(),
                   content=content, active=p.is_published)


@receiver(post_save, sender=FAQ)
def _faq_saved(sender, instance, **kwargs):
    sync_faq(instance)


@receiver(post_delete, sender=FAQ)
def _faq_deleted(sender, instance, **kwargs):
    _remove(f"faq:{instance.pk}")


@receiver(post_save, sender=Service)
def _service_saved(sender, instance, **kwargs):
    sync_service(instance)


@receiver(post_delete, sender=Service)
def _service_deleted(sender, instance, **kwargs):
    _remove(f"service:{instance.pk}")


@receiver(post_save, sender=PortfolioProject)
def _project_saved(sender, instance, **kwargs):
    sync_project(instance)


@receiver(post_delete, sender=PortfolioProject)
def _project_deleted(sender, instance, **kwargs):
    _remove(f"project:{instance.pk}")


@receiver(post_save, sender=ProjectRoom)
@receiver(post_save, sender=ProjectSwatch)
def _project_part_saved(sender, instance, **kwargs):
    if instance.project_id and not kwargs.get("raw"):
        sync_project(instance.project)


@receiver(post_save, sender=KnowledgeDocument)
def _doc_saved(sender, instance, **kwargs):
    if not instance.source_key:  # synced docs are indexed by _upsert already
        rag.index_document(instance)


@receiver(post_delete, sender=KnowledgeDocument)
def _doc_deleted(sender, instance, **kwargs):
    rag.bump_version()


def sync_all():
    for f in FAQ.objects.all():
        sync_faq(f)
    for s in Service.objects.all():
        sync_service(s)
    for p in PortfolioProject.objects.prefetch_related("rooms", "swatches"):
        sync_project(p)
