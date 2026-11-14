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


# ------------------------------------------------------------------ 360° house tour (extra feature)
# The studio normally edits tours in the studio (Website content → 360° house tour) where dots are placed by
# clicking on the photo. These admin pages are for DEVNIXPLUS support.
from django import forms  # noqa: E402

from .models import Tour, TourHotspot, TourRoom  # noqa: E402


class TourRoomAdminForm(forms.ModelForm):
    class Meta:
        model = TourRoom
        fields = "__all__"

    def clean_panorama(self):
        from .tour360 import process_panorama
        f = self.cleaned_data.get("panorama")
        self.processed = process_panorama(f) if f and hasattr(f, "content_type") else None
        return f


class TourRoomInline(admin.TabularInline):
    model = TourRoom
    extra = 0
    fields = ["title", "icon", "order"]
    show_change_link = True


class TourHotspotInline(admin.StackedInline):
    model = TourHotspot
    fk_name = "room"
    extra = 0
    fields = [("kind", "order"), ("yaw", "pitch"), "link_to", ("tag", "title"), "text", "specs"]


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ["title", "is_published", "is_sample", "order"]
    list_editable = ["is_published", "order"]
    inlines = [TourRoomInline]


@admin.register(TourRoom)
class TourRoomAdmin(admin.ModelAdmin):
    form = TourRoomAdminForm
    list_display = ["title", "tour", "order"]
    list_filter = ["tour"]
    inlines = [TourHotspotInline]

    def save_model(self, request, obj, form, change):
        if getattr(form, "processed", None):
            pano, prev = form.processed
            obj.panorama.save(pano.name, pano, save=False)
            obj.preview.save(prev.name, prev, save=False)
        super().save_model(request, obj, form, change)
