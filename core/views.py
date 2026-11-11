from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .permissions import is_client, is_team

from . import locked
from .models import FeatureInterest
from .templatetags.studio import wa_link


@require_POST
def feature_interest(request, key):
    if key not in locked.LOCKED_FEATURES:
        raise Http404
    if not request.session.session_key:
        request.session.save()
    feature = locked.get(key)
    FeatureInterest.objects.create(feature=feature["title"], session_key=request.session.session_key or "")
    text = f"Hi {settings.DEVNIX_NAME}, I saw the interior studio demo and I want this feature: {feature['title']}."
    return JsonResponse({"ok": True, "wa_url": wa_link(settings.DEVNIX_WHATSAPP, text) if settings.DEVNIX_WHATSAPP else ""})


def after_login(request):
    """Send each role to its home after signing in."""
    if is_team(request.user):
        from .modules import studio_home_url
        return redirect(studio_home_url())
    if is_client(request.user):
        return redirect("portal:overview")
    return redirect(_site_home())


def _site_home():
    return reverse("website:home") if settings.LANDING_PAGE else "/"


DEMO_ROLES = {"owner": "owner", "designer": "designer", "client": "client"}


@require_POST
def switch_role(request, role):
    """Demo only: jump between Visitor / Owner / Team member / Client without typing passwords."""
    if not settings.DEMO_MODE:
        raise Http404
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        nxt = ""
    quiet = request.POST.get("quiet") == "1"
    if role == "visitor":
        logout(request)
        if not quiet:
            messages.info(request, "You are now viewing the site as a visitor.")
        return redirect(nxt or _site_home())
    username = DEMO_ROLES.get(role)
    user = User.objects.filter(username=username, is_active=True).first() if username else None
    if not user:
        raise Http404
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    if not quiet:
        messages.info(request, f"Signed in as {user.get_full_name() or user.username} ({role}).")
    if nxt:
        return redirect(nxt)
    return redirect("studio:dashboard" if is_team(user) else "portal:overview" if is_client(user) else _site_home())
