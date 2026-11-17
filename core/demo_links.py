"""Personal demo links for prospects (DEVNIXPLUS sales, demo mode only).

    /d/sharma-interiors/  →  the whole demo shows “Sharma Interiors” (city, logo, colours) for that visitor,
                             and every open, page and click is recorded on the link in /admin/.

The brand lives in a signed cookie (it survives the demo's role switches, which log in and out) and is applied
per request through a context variable that StudioSettings.load() reads. Nothing is written to the real settings.
"""
import contextvars
import copy
import re
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db.models import F
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

COOKIE = "demo_brand"
SALT = "core.demo_links"
COOKIE_AGE = 60 * 60 * 24 * 90          # 90 days: a prospect often comes back a week later
NEW_VISIT_AFTER = timedelta(minutes=30)
SAME_PAGE_GAP = timedelta(minutes=2)    # reloading a page doesn't count twice
SKIP_PATHS = ("/admin/", "/static/", "/media/", "/d/", "/demo/track/", "/favicon")
TEXT_FIELDS = ["tagline", "hero_title", "hero_subtitle", "about_text", "quotation_terms", "bank_details",
               "address", "map_embed_query", "legal_name"]

# Clicks the page may report (anything else is ignored)
ACTIONS = {
    "tour360": "Opened the 360° house tour",
    "tour": "Started the guided demo tour",
    "whatsapp": "Clicked “Talk to us” on WhatsApp",
}

_current = contextvars.ContextVar("demo_link", default=None)


# ------------------------------------------------------------------ applying the brand
def branded(obj):
    """StudioSettings as the current demo-link visitor should see it (the object itself when there is no link)."""
    link = _current.get()
    if link is None:
        return obj
    s = copy.copy(obj)
    original = {}

    def put(field, value):
        current = getattr(s, field)
        real = original[field][0] if field in original else getattr(current, "name", current)
        original[field] = (real, getattr(value, "name", value))
        setattr(s, field, value)

    old_name, old_city = obj.name, obj.city
    pairs = [(old_name, link.business_name)]
    old_first, new_first = old_name.split()[0] if old_name else "", link.business_name.split()[0]
    if len(old_first) > 3 and old_first != new_first:
        pairs.append((old_first, new_first))
    if link.city and old_city and link.city != old_city:
        pairs.append((old_city, link.city))
    for field in TEXT_FIELDS:
        text = getattr(s, field) or ""
        new = text
        for a, b in pairs:
            new = new.replace(a, b)
        if new != text:
            put(field, new)
    put("name", link.business_name)
    if link.city:
        put("city", link.city)
    slug = re.sub(r"[^a-z0-9]", "", link.business_name.lower())[:30] or "studio"
    put("email", f"hello@{slug}.in")
    if s.instagram:
        put("instagram", slug)
    if link.logo:
        put("logo", link.logo.name)
    elif s.logo:
        put("logo", "")        # the demo studio's logo would look wrong next to another name
    if link.accent_color and link.secondary_color and link.dark_color:
        put("accent_color", link.accent_color)
        put("secondary_color", link.secondary_color)
        put("dark_color", link.dark_color)
    s._brand_original = original
    return s


def current_link():
    return _current.get()


# ------------------------------------------------------------------ helpers
def _device(request):
    ua = request.META.get("HTTP_USER_AGENT", "")
    if re.search(r"iPad|Tablet", ua):
        return "Tablet"
    if re.search(r"Mobi|Android|iPhone", ua):
        return "Mobile"
    return "Computer" if ua else ""


def _track(request):
    """Record activity unless this is DEVNIXPLUS looking at it (preview link or a superuser)."""
    return not getattr(request, "demo_preview", False) and not getattr(request.user, "is_superuser", False)


def _touch(link, request, kind, path="", title=""):
    from .models import DemoLink, DemoVisit
    now = timezone.now()
    updates = {"last_seen_at": now}
    if link.first_opened_at is None:
        updates["first_opened_at"] = now
    if kind == "page":
        updates["page_views"] = F("page_views") + 1
    if link.last_seen_at is None or now - link.last_seen_at > NEW_VISIT_AFTER:
        updates["visits"] = F("visits") + 1
    DemoLink.objects.filter(pk=link.pk).update(**updates)
    link.last_seen_at = now
    DemoVisit.objects.create(link=link, kind=kind, path=path[:300], title=title[:160], device=_device(request))


# ------------------------------------------------------------------ views
def open_link(request, slug):
    """/d/<slug>/ — brand the demo for this prospect and start on the website."""
    if not settings.DEMO_MODE:
        raise Http404
    from .models import DemoLink
    link = get_object_or_404(DemoLink, slug=slug)
    home = reverse("website:home") if settings.LANDING_PAGE else "/"
    resp = redirect(home)
    if not link.is_active:
        resp.delete_cookie(COOKIE)
        return resp
    preview = request.GET.get("preview") == "1" and request.user.is_superuser
    request.demo_preview = preview
    if _track(request):
        _touch(link, request, "open", request.get_full_path())
    first = link.contact_name.split()[0] if link.contact_name else ""
    messages.info(request, (f"Welcome, {first}! " if first else "Welcome! ")
                  + f"This demo is set up for {link.business_name}. Use the Tour button to see everything.")
    resp.set_signed_cookie(COOKIE, f"{link.slug}:{'p' if preview else 'c'}", salt=SALT, max_age=COOKIE_AGE,
                           httponly=True, samesite="Lax", secure=request.is_secure())
    return resp


@csrf_exempt     # only adds a row from a fixed list to the visitor's own link; nothing else can be done with it
@require_POST
def track(request):
    link = getattr(request, "demo_link", None)
    what = request.POST.get("what", "")
    if link and what in ACTIONS and _track(request):
        _touch(link, request, "action", request.POST.get("path", "")[:300], ACTIONS[what])
    return HttpResponse(status=204)


# ------------------------------------------------------------------ middleware
class DemoBrandMiddleware:
    """Applies the prospect's brand for the whole request and records the pages they view."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw = request.get_signed_cookie(COOKIE, default=None, salt=SALT) if settings.DEMO_MODE else None
        if not raw:
            return self.get_response(request)
        from .models import DemoLink
        slug, _, mode = raw.partition(":")
        link = DemoLink.objects.filter(slug=slug, is_active=True).first()
        if link is None:
            resp = self.get_response(request)
            resp.delete_cookie(COOKIE)
            return resp
        request.demo_link, request.demo_preview = link, mode == "p"
        token = _current.set(link)
        try:
            resp = self.get_response(request)
        finally:
            _current.reset(token)
        if (request.method == "GET" and resp.status_code == 200 and not request.path.startswith(SKIP_PATHS)
                and "text/html" in resp.get("Content-Type", "") and not getattr(resp, "streaming", False)
                and request.headers.get("x-requested-with") != "XMLHttpRequest" and _track(request)):
            self._page(request, link, resp)
        return resp

    def _page(self, request, link, resp):
        from .models import DemoVisit
        last = DemoVisit.objects.filter(link=link).only("path", "created_at").first()
        if last and last.path == request.path and timezone.now() - last.created_at < SAME_PAGE_GAP:
            return
        m = re.search(rb"<title>(.*?)</title>", resp.content[:4000], re.S | re.I)
        title = ""
        if m:
            from html import unescape
            title = unescape(m.group(1).decode("utf-8", "ignore")).strip()
            title = re.sub(r"\s*[—|–-]\s*" + re.escape(link.business_name) + r".*$", "", title) or title
        _touch(link, request, "page", request.path, title)
