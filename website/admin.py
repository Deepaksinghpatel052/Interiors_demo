from django.contrib import admin

from .models import (FAQ, BeforeAfter, PhotoCredit, PortfolioProject, ProjectImage, ProjectRoom,
                     ProjectSwatch, Service, Testimonial, TimelineStep)


class ImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 0


class BeforeAfterInline(admin.TabularInline):
    model = BeforeAfter
    extra = 0


class RoomInline(admin.StackedInline):
    model = ProjectRoom
    extra = 0


class SwatchInline(admin.TabularInline):
    model = ProjectSwatch
    extra = 0


class TimelineInline(admin.TabularInline):
    model = TimelineStep
    extra = 0


@admin.register(PortfolioProject)
class PortfolioProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "room_type", "style", "budget_band", "is_featured", "is_published", "order"]
    list_editable = ["is_featured", "is_published", "order"]
    list_filter = ["room_type", "style", "budget_band"]
    search_fields = ["title", "location"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [ImageInline, BeforeAfterInline, RoomInline, SwatchInline, TimelineInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["title", "order", "is_active"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ["title"]}


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "is_sample", "is_active"]


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ["question", "category", "order", "is_active"]
    list_filter = ["category"]


admin.site.register(PhotoCredit)


from .models import Package  # noqa: E402


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "price_text", "order", "is_active")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"key": ("name",)}
