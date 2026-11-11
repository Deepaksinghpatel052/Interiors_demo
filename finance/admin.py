from django.contrib import admin

from .models import CatalogueItem, Invoice, Payment, PaymentScheduleItem, Quotation, QuotationItem, QuotationRoom, Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "contact_person", "phone", "city", "is_active"]
    list_filter = ["category"]


@admin.register(CatalogueItem)
class CatalogueItemAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "unit", "rate", "gst_percent", "vendor", "is_active"]
    list_filter = ["category"]
    search_fields = ["name"]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["number", "project", "date", "total", "status"]
    list_filter = ["status", "financial_year"]
    inlines = [PaymentInline]


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ["number", "version", "client_name", "date", "status", "grand_total"]
    list_filter = ["status"]


admin.site.register([QuotationRoom, QuotationItem, PaymentScheduleItem, Payment])
