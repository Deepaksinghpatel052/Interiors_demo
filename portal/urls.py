from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("designs/", views.designs, name="designs"),
    path("designs/<int:pk>/", views.design_detail, name="design_detail"),
    path("designs/<int:pk>/action/", views.design_action, name="design_action"),
    path("timeline/", views.timeline, name="timeline"),
    path("updates/", views.updates, name="updates"),
    path("documents/", views.documents, name="documents"),
    path("documents/<int:pk>/download/", views.document_download, name="document_download"),
    path("quotations/<int:pk>/pdf/", views.quotation_pdf, name="quotation_pdf"),
    path("invoices/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("payments/", views.payments, name="payments"),
    path("requests/", views.requests_view, name="requests"),
]
