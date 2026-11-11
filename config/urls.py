from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from django.views.generic import RedirectView

from core.landing import root

admin.site.site_header = "Studio administration"
admin.site.site_title = "Studio admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", root, name="landing"),
    path("product/", RedirectView.as_view(url="/", permanent=False)),
    path("", include("core.urls")),
    path("", include("website.urls")),
    path("", include("bookings.urls")),
    path("studio/", include("studio.urls")),
    path("studio/", include("finance.urls")),
    path("studio/automations/", include("automations.urls")),
    path("studio/website/", include("website.cms_urls")),
    path("portal/", include("portal.urls")),
    path("", include("assistant.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
