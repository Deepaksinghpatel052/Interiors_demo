from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class RoomType(models.TextChoices):
    LIVING = "living", "Living room"
    BEDROOM = "bedroom", "Bedroom"
    KITCHEN = "kitchen", "Kitchen"
    OFFICE = "office", "Office"
    RETAIL = "retail", "Retail"
    FULL_HOME = "full_home", "Full home"


class Style(models.TextChoices):
    MODERN = "modern", "Modern"
    CONTEMPORARY = "contemporary", "Contemporary"
    TRADITIONAL = "traditional", "Traditional Indian"
    MINIMAL = "minimal", "Minimal"
    LUXURY = "luxury", "Luxury"


class BudgetBand(models.TextChoices):
    UNDER_5 = "under_5", "Under ₹5 lakh"
    B5_10 = "5_10", "₹5–10 lakh"
    B10_20 = "10_20", "₹10–20 lakh"
    B20_40 = "20_40", "₹20–40 lakh"
    ABOVE_40 = "above_40", "Above ₹40 lakh"


class PropertyType(models.TextChoices):
    BHK1 = "1bhk", "1 BHK"
    BHK2 = "2bhk", "2 BHK"
    BHK3 = "3bhk", "3 BHK"
    BHK4 = "4bhk", "4 BHK+"
    VILLA = "villa", "Villa / Bungalow"
    OFFICE = "office", "Office"
    RETAIL = "retail", "Retail / Showroom"


class PortfolioProject(models.Model):
    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    location = models.CharField(max_length=80, help_text="Area and city, e.g. Vijay Nagar, Indore")
    room_type = models.CharField(max_length=20, choices=RoomType.choices)
    style = models.CharField(max_length=20, choices=Style.choices)
    budget_band = models.CharField(max_length=20, choices=BudgetBand.choices)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices, blank=True)
    area_sqft = models.PositiveIntegerField(default=0)
    duration_weeks = models.PositiveIntegerField(default=8)
    year = models.PositiveIntegerField(default=2025)
    summary = models.CharField(max_length=240)
    description = models.TextField()
    brief = models.TextField(blank=True, help_text="What the client asked for.")
    client_quote = models.TextField(blank=True)
    client_name = models.CharField(max_length=80, blank=True)
    cover = models.ImageField(upload_to="portfolio/covers/")
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-year", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:150] or "project"
            slug, n = base, 2
            while PortfolioProject.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("website:project_detail", args=[self.slug])

    @property
    def colours(self):
        return self.swatches.filter(kind=ProjectSwatch.Kind.COLOUR)

    @property
    def materials(self):
        return self.swatches.filter(kind=ProjectSwatch.Kind.MATERIAL)


class ProjectImage(models.Model):
    project = models.ForeignKey(PortfolioProject, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="portfolio/gallery/")
    caption = models.CharField(max_length=160, blank=True)
    room = models.CharField(max_length=60, blank=True)
    in_mood_board = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.caption or f"Image {self.pk}"


class BeforeAfter(models.Model):
    project = models.ForeignKey(PortfolioProject, related_name="before_afters", on_delete=models.CASCADE)
    before = models.ImageField(upload_to="portfolio/before_after/")
    after = models.ImageField(upload_to="portfolio/before_after/")
    caption = models.CharField(max_length=160, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Before / after pair"


class ProjectRoom(models.Model):
    project = models.ForeignKey(PortfolioProject, related_name="rooms", on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class ProjectSwatch(models.Model):
    class Kind(models.TextChoices):
        COLOUR = "colour", "Colour"
        MATERIAL = "material", "Material"

    project = models.ForeignKey(PortfolioProject, related_name="swatches", on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.COLOUR)
    name = models.CharField(max_length=80)
    hex = models.CharField(max_length=7, default="#CCCCCC")
    note = models.CharField(max_length=120, blank=True, help_text="e.g. 'Matte laminate, 1 mm'")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["kind", "order", "id"]


class TimelineStep(models.Model):
    project = models.ForeignKey(PortfolioProject, related_name="timeline", on_delete=models.CASCADE)
    title = models.CharField(max_length=80)
    duration = models.CharField(max_length=40, help_text="e.g. 'Week 1–2'")
    description = models.CharField(max_length=240, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class Service(models.Model):
    title = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=40, default="house-heart", help_text="Bootstrap Icons name")
    short = models.CharField(max_length=180)
    description = models.TextField()
    includes = models.TextField(blank=True, help_text="One item per line")
    typical_timeline = models.CharField(max_length=60, blank=True)
    image = models.ImageField(upload_to="services/", blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Testimonial(models.Model):
    name = models.CharField(max_length=80)
    city = models.CharField(max_length=60, blank=True)
    project_type = models.CharField(max_length=80, blank=True)
    text = models.TextField()
    is_sample = models.BooleanField(default=True, help_text="Shown with a 'Sample' label on the site.")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class FAQ(models.Model):
    question = models.CharField(max_length=200)
    answer = models.TextField()
    category = models.CharField(max_length=40, default="General")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "order", "id"]
        verbose_name = "FAQ"

    def __str__(self):
        return self.question


class PhotoCredit(models.Model):
    description = models.CharField(max_length=200)
    author = models.CharField(max_length=120)
    source = models.CharField(max_length=60)
    url = models.URLField(blank=True)

    def __str__(self):
        return f"{self.description} — {self.author}"


class Package(models.Model):
    """DEVNIXPLUS offer modules shown on /why (demo mode). Prices are empty unless the seller fills them in."""
    key = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=60)
    tagline = models.CharField(max_length=160, blank=True)
    includes = models.TextField(blank=True, help_text="One item per line.")
    price_text = models.CharField(max_length=80, blank=True,
                                  help_text="Optional, e.g. “from ₹… + GST”. Leave empty to show “Talk to us”.")
    icon = models.CharField(max_length=40, default="box", help_text="Bootstrap icon name, e.g. globe2")
    is_bundle = models.BooleanField(default=False, help_text="Complete system: includes every other module.")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def include_list(self):
        return [line.strip() for line in self.includes.splitlines() if line.strip()]


# ------------------------------------------------------------------ 360° house tour (extra feature, on request)
class Tour(models.Model):
    """A walk-through made of 360° room photos. The first published tour is shown on the portfolio page."""
    title = models.CharField(max_length=80, help_text="e.g. “Aangan Residence”")
    subtitle = models.CharField(max_length=140, blank=True,
                                help_text="Short line under the title on the portfolio card. Empty: the room names.")
    is_published = models.BooleanField("Show on the website", default=True)
    is_sample = models.BooleanField(default=False, help_text="Sample content that came with the system.")
    order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "360° house tour"

    def __str__(self):
        return self.title


class TourRoom(models.Model):
    class Icon(models.TextChoices):
        LIVING = "bi-tv", "Living / lounge"
        KITCHEN = "bi-cup-hot", "Kitchen"
        DINING = "bi-egg-fried", "Dining"
        BEDROOM = "bi-moon-stars", "Bedroom"
        BATH = "bi-droplet", "Bathroom"
        STUDY = "bi-laptop", "Study / office"
        KIDS = "bi-balloon", "Kids’ room"
        OUTDOOR = "bi-tree", "Balcony / outdoor"
        ENTRANCE = "bi-door-open", "Entrance / foyer"
        OTHER = "bi-house", "Other"

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="rooms")
    title = models.CharField(max_length=60, help_text="e.g. “Living lounge”")
    icon = models.CharField(max_length=20, choices=Icon.choices, default=Icon.LIVING)
    panorama = models.ImageField("360° photo", upload_to="tours/",
                                 help_text="A 360° photo in 2:1 shape (equirectangular), e.g. from a 360° camera or phone app.")
    preview = models.ImageField(upload_to="tours/previews/", blank=True, editable=False)
    start_yaw = models.FloatField("Start: left/right", default=0)
    start_pitch = models.FloatField("Start: up/down", default=0)
    start_hfov = models.FloatField("Start: zoom (field of view)", default=105)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.tour} — {self.title}"


class TourHotspot(models.Model):
    class Kind(models.TextChoices):
        INFO = "info", "Info dot"
        LINK = "link", "Arrow to another room"

    room = models.ForeignKey(TourRoom, on_delete=models.CASCADE, related_name="hotspots")
    kind = models.CharField(max_length=4, choices=Kind.choices, default=Kind.INFO)
    yaw = models.FloatField(help_text="Left/right angle, -180 to 180")
    pitch = models.FloatField(help_text="Up/down angle, -90 to 90")
    tag = models.CharField("Category", max_length=30, blank=True, help_text="e.g. Furniture, Lighting, Flooring")
    title = models.CharField(max_length=80, blank=True)
    text = models.TextField("Description", blank=True)
    specs = models.TextField("Details", blank=True, help_text="One per line, e.g. “Fabric: performance linen”.")
    link_to = models.ForeignKey(TourRoom, on_delete=models.CASCADE, null=True, blank=True, related_name="+",
                                verbose_name="Goes to room")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title or (f"→ {self.link_to.title}" if self.link_to_id else "Hotspot")

    @property
    def spec_list(self):
        return [line.strip() for line in self.specs.splitlines() if line.strip()]
