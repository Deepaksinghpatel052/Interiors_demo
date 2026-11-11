from django.urls import path

from . import views

app_name = "automations"

urlpatterns = [
    path("", views.automations, name="index"),
    path("run/", views.run_now, name="run"),
    path("<slug:key>/save/", views.template_save, name="save"),
    path("<slug:key>/toggle/", views.template_toggle, name="toggle"),
]
