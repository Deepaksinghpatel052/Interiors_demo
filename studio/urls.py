from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # leads
    path("leads/", views.leads_board, name="leads"),
    path("leads/new/", views.lead_create, name="lead_create"),
    path("leads/move/", views.lead_move, name="lead_move"),
    path("leads/<int:pk>/", views.lead_detail, name="lead_detail"),
    path("leads/<int:pk>/note/", views.lead_note, name="lead_note"),
    path("leads/<int:pk>/convert/", views.lead_convert, name="lead_convert"),
    # bookings
    path("bookings/", views.bookings_calendar, name="bookings"),
    path("bookings/events/", views.bookings_events, name="booking_events"),
    path("bookings/availability/", views.availability, name="availability"),
    path("bookings/unblock/<int:pk>/", views.unblock_date, name="unblock_date"),
    path("bookings/<int:pk>/move/", views.booking_move, name="booking_move"),
    path("bookings/<int:pk>/status/", views.booking_status, name="booking_status"),
    # projects
    path("projects/", views.projects, name="projects"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/move/", views.project_move, name="project_move"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),
    path("projects/<int:pk>/edit/", views.project_edit, name="project_edit"),
    path("projects/<int:pk>/tasks/add/", views.task_add, name="task_add"),
    path("projects/<int:pk>/milestones/add/", views.milestone_add, name="milestone_add"),
    path("projects/<int:pk>/rooms/add/", views.space_add, name="space_add"),
    path("projects/<int:pk>/designs/add/", views.proposal_add, name="proposal_add"),
    path("projects/<int:pk>/updates/add/", views.update_add, name="update_add"),
    path("projects/<int:pk>/documents/add/", views.document_add, name="document_add"),
    path("tasks/", views.my_tasks, name="tasks"),
    path("tasks/<int:pk>/status/", views.task_status, name="task_status"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("milestones/<int:pk>/status/", views.milestone_status, name="milestone_status"),
    path("rooms/<int:pk>/delete/", views.space_delete, name="space_delete"),
    path("designs/<int:pk>/share/", views.proposal_share, name="proposal_share"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
    path("settings/", views.studio_settings, name="settings"),
    path("team/", views.team, name="team"),
    path("reports/", views.reports, name="reports"),
    path("reports/<slug:kind>.csv", views.report_csv, name="report_csv"),
    path("api/client-activity/", views.client_activity, name="client_activity"),
]
