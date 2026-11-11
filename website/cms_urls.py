from django.urls import path

from . import cms

app_name = "cms"

urlpatterns = [
    path("", cms.index, name="index"),
    path("projects/", cms.projects, name="projects"),
    path("projects/new/", cms.project_edit, name="project_new"),
    path("projects/<int:pk>/", cms.project_edit, name="project_edit"),
    path("projects/<int:pk>/photos/", cms.project_media, name="project_media"),
    path("projects/<int:pk>/mood-board/", cms.project_moodboard, name="project_moodboard"),
    path("projects/<int:pk>/delete/", cms.project_delete, name="project_delete"),
    path("<slug:kind>/", cms.item_list, name="list"),
    path("<slug:kind>/new/", cms.item_edit, name="new"),
    path("<slug:kind>/<int:pk>/", cms.item_edit, name="edit"),
    path("<slug:kind>/<int:pk>/delete/", cms.item_delete, name="delete"),
]
