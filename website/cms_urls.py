from django.urls import path

from . import cms, cms_tours

app_name = "cms"

urlpatterns = [
    path("", cms.index, name="index"),
    path("projects/", cms.projects, name="projects"),
    path("projects/new/", cms.project_edit, name="project_new"),
    path("projects/<int:pk>/", cms.project_edit, name="project_edit"),
    path("projects/<int:pk>/photos/", cms.project_media, name="project_media"),
    path("projects/<int:pk>/mood-board/", cms.project_moodboard, name="project_moodboard"),
    path("projects/<int:pk>/delete/", cms.project_delete, name="project_delete"),
    # 360° house tour (extra feature, switched on by DEVNIXPLUS on request)
    path("tours/", cms_tours.tours, name="tours"),
    path("tours/request/", cms_tours.tour_request, name="tour_request"),
    path("tours/new/", cms_tours.tour_edit, name="tour_new"),
    path("tours/<int:pk>/", cms_tours.tour_edit, name="tour_edit"),
    path("tours/<int:pk>/delete/", cms_tours.tour_delete, name="tour_delete"),
    path("tours/<int:tour>/rooms/new/", cms_tours.room_edit, name="tour_room_new"),
    path("tours/<int:tour>/rooms/<int:pk>/", cms_tours.room_edit, name="tour_room"),
    path("tours/<int:tour>/rooms/<int:pk>/delete/", cms_tours.room_delete, name="tour_room_delete"),
    path("<slug:kind>/", cms.item_list, name="list"),
    path("<slug:kind>/new/", cms.item_edit, name="new"),
    path("<slug:kind>/<int:pk>/", cms.item_edit, name="edit"),
    path("<slug:kind>/<int:pk>/delete/", cms.item_delete, name="delete"),
]
