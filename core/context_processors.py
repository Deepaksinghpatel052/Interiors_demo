from django.conf import settings
from django.urls import reverse

from .locked import LOCKED_FEATURES
from .models import StudioSettings
from .modules import MODULES, studio_home_url
from .permissions import role_of
from .tour import steps as tour_steps


def studio(request):
    s = StudioSettings.load()
    return {
        "studio": s,
        "DEMO_MODE": settings.DEMO_MODE,
        "AI_MOCK": settings.AI_MOCK,
        "DEVNIX_WHATSAPP": settings.DEVNIX_WHATSAPP,
        "DEVNIX_NAME": settings.DEVNIX_NAME,
        "erp_role": role_of(request.user) if hasattr(request, "user") else "visitor",
        "demo_roles": [("visitor", "Visitor (website)", "globe2"), ("owner", "Designer-owner (studio)", "briefcase"),
                       ("designer", "Team member", "person-workspace"), ("client", "Client (portal)", "person-heart")],
        "demo_ribbon_hidden": request.COOKIES.get("demo_ribbon") == "hidden",
        "off_modules": [(k, label, icon) for k, label, icon, _ in MODULES if not getattr(s, "module_" + k, True)],
        "studio_home": studio_home_url(s),
        "site_home": reverse("website:home") if settings.LANDING_PAGE else "/",
        "tour_steps": tour_steps(s) if settings.DEMO_MODE else None,
        "locked_features": {k: {"title": t, "what": w, "benefit": b} for k, (t, w, b) in LOCKED_FEATURES.items()},
    }
