from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("quotations/", views.quotation_list, name="quotations"),
    path("quotations/new/", views.quotation_new, name="quotation_new"),
    path("quotations/<int:pk>/", views.quotation_detail, name="quotation_detail"),
    path("quotations/<int:pk>/save/", views.quotation_save, name="quotation_save"),
    path("quotations/<int:pk>/send/", views.quotation_send, name="quotation_send"),
    path("quotations/<int:pk>/accept/", views.quotation_accept, name="quotation_accept"),
    path("quotations/<int:pk>/reject/", views.quotation_reject, name="quotation_reject"),
    path("quotations/<int:pk>/revise/", views.quotation_revise, name="quotation_revise"),
    path("quotations/<int:pk>/pdf/", views.quotation_pdf, name="quotation_pdf"),
    path("invoices/", views.invoice_list, name="invoices"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/pay/", views.invoice_pay, name="invoice_pay"),
    path("invoices/<int:pk>/cancel/", views.invoice_cancel, name="invoice_cancel"),
    path("invoices/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("schedule/<int:pk>/invoice/", views.schedule_invoice, name="schedule_invoice"),
    path("vendors/", views.vendor_list, name="vendors"),
    path("vendors/<int:pk>/", views.vendor_edit, name="vendor_edit"),
    path("vendors/<int:pk>/delete/", views.vendor_delete, name="vendor_delete"),
    path("catalogue/", views.catalogue_list, name="catalogue"),
    path("catalogue/<int:pk>/", views.catalogue_edit, name="catalogue_edit"),
    path("catalogue/<int:pk>/delete/", views.catalogue_delete, name="catalogue_delete"),
]
