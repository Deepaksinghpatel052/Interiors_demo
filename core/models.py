from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models

hex_color = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use a hex colour like #B5651D.")

CACHE_KEY = "studio_settings_v1"


def default_payment_schedule():
    return [
        {"label": "Booking advance", "percent": 10},
        {"label": "On design approval", "percent": 40},
        {"label": "Mid-execution", "percent": 40},
        {"label": "On handover", "percent": 10},
    ]


class StudioSettings(models.Model):
    """Singleton holding everything that is client-specific (white-label)."""

    # Brand
    name = models.CharField(max_length=120, default="Aangan Interiors")
    tagline = models.CharField(max_length=200, default="Homes designed around the way you live.")
    logo = models.ImageField(upload_to="brand/", blank=True)
    accent_color = models.CharField("Primary colour", max_length=7, default="#0081F6", validators=[hex_color],
                                    help_text="Buttons, links and highlights, e.g. blue #0081F6.")
    secondary_color = models.CharField("Secondary colour", max_length=7, default="#2474F8", validators=[hex_color],
                                       help_text="Second shade used in gradients and hover states, e.g. #2474F8.")
    dark_color = models.CharField("Dark colour", max_length=7, default="#111212", validators=[hex_color],
                                  help_text="Text, dark sections, footer and studio sidebar, e.g. #111212.")

    # Contact
    city = models.CharField(max_length=80, default="Indore")
    address = models.TextField(default="2nd Floor, Shree Complex, Vijay Nagar, Indore, Madhya Pradesh 452010")
    phone = models.CharField(max_length=20, default="+91 98270 00000")
    whatsapp = models.CharField(max_length=15, default="919827000000",
                                help_text="Country code + number, digits only, e.g. 919827000000")
    email = models.EmailField(default="hello@aanganinteriors.in")
    map_embed_query = models.CharField(max_length=200, default="Vijay Nagar, Indore",
                                       help_text="Text used for the Google Maps embed.")
    instagram = models.CharField(max_length=100, blank=True, default="aanganinteriors")
    working_hours = models.CharField(max_length=120, default="Mon–Sat, 10:00 AM – 7:00 PM")
    founded_year = models.PositiveIntegerField(default=2014)

    # Website copy
    hero_title = models.CharField(max_length=160, default="Interiors that feel like home, from the first sketch to the last cushion.")
    hero_subtitle = models.CharField(max_length=300, default="Residential and commercial interiors, designed with care and executed on time — with every design, quote and payment visible to you online.")
    about_text = models.TextField(default=(
        "We are a small, design-led studio that believes good interiors begin with listening. "
        "Every home we design starts with how you live — your mornings, your festivals, your storage, "
        "your light — and ends with a space that is calm, practical and unmistakably yours."
    ))

    # Tax / commercial
    legal_name = models.CharField(max_length=160, default="Aangan Interiors LLP")
    gstin = models.CharField(max_length=15, blank=True, default="23ABCDE1234F1Z5")
    state_name = models.CharField(max_length=60, default="Madhya Pradesh")
    default_gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    payment_schedule = models.JSONField(default=default_payment_schedule)
    quotation_terms = models.TextField(default=(
        "Rates are valid for 30 days from the quotation date.\n"
        "Civil, electrical and plumbing work is quoted separately unless listed.\n"
        "Final measurements are taken after the site visit; quantities may vary."
    ))
    bank_details = models.TextField(default="Aangan Interiors LLP · HDFC Bank · A/c 50200012345678 · IFSC HDFC0001234 · UPI aangan@hdfcbank")

    # Cost estimator rates (₹ per sq ft of carpet area)
    rate_essential = models.PositiveIntegerField(default=1200)
    rate_premium = models.PositiveIntegerField(default=1900)
    rate_luxury = models.PositiveIntegerField(default=3000)

    # Sales copy
    easy_payment_text = models.TextField(blank=True, default=(
        "Pay in 3 parts: on booking, on approval of the design, and on go-live.\n"
        "Or choose a one-time setup fee plus a small monthly plan."
    ))

    # Module feature flags (sell the same codebase as small or complete packages)
    module_website = models.BooleanField("Website", default=True)
    module_cms = models.BooleanField("Website CMS", default=True)
    module_portal = models.BooleanField("Client portal", default=True)
    module_erp = models.BooleanField("Studio ERP", default=True)
    module_automation = models.BooleanField("Automation", default=True)
    module_ai = models.BooleanField("AI assistant", default=True)
    show_locked_teasers = models.BooleanField(
        default=True, help_text="Show full-version features as locked teasers instead of hiding them.")

    # Extra features: off until the studio requests them and DEVNIXPLUS switches them on (Django admin only)
    module_tour360 = models.BooleanField(
        "360° house tour", default=False,
        help_text="Extra feature, switched on by DEVNIXPLUS on request: 360° room walk-through on the portfolio page.")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Studio settings"
        verbose_name_plural = "Studio settings"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # A copy branded for a client demo link (core.demo_links) must never write the client's name into
        # the real settings: fields still showing the branded value get their real value back.
        for field, (real, shown) in getattr(self, "_brand_original", {}).items():
            current = getattr(self, field)
            if (getattr(current, "name", current) or "") == (shown or ""):
                setattr(self, field, real)
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)

    def delete(self, *args, **kwargs):  # singleton: never delete
        return None

    @classmethod
    def load(cls):
        obj = cache.get(CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(CACHE_KEY, obj, 300)
        from .demo_links import branded   # a visitor on a client demo link sees that client's name
        return branded(obj)

    @property
    def initials(self):
        parts = [p for p in self.name.split() if p[:1].isalpha()]
        return "".join(p[0] for p in parts[:2]).upper() or "S"

    @property
    def phone_digits(self):
        return "".join(c for c in self.phone if c.isdigit() or c == "+")

    @property
    def years_of_practice(self):
        from django.utils import timezone
        return max(1, timezone.localdate().year - self.founded_year)


class FeatureInterest(models.Model):
    """A prospect clicked “I want this feature” on a locked teaser."""

    feature = models.CharField(max_length=80)
    session_key = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.feature} @ {self.created_at:%d-%m-%Y %H:%M}"


class ModuleRequest(models.Model):
    """The studio asked DEVNIXPLUS to switch on an extra feature (see core.modules.EXTRA_FEATURES)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Waiting"
        APPROVED = "approved", "Switched on"
        DECLINED = "declined", "Declined"

    feature = models.CharField(max_length=30)
    requested_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    note = models.TextField("Message", blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Extra-feature request"

    def __str__(self):
        return f"{self.feature_label} ({self.get_status_display()})"

    @property
    def feature_label(self):
        from .modules import EXTRA_FEATURES
        return EXTRA_FEATURES.get(self.feature, {}).get("label", self.feature)


class ProductEnquiry(models.Model):
    """An interior designer asking DEVNIXPLUS about the product (from the landing page). Seller's lead, not the studio's."""

    class TeamSize(models.TextChoices):
        SOLO = "solo", "Just me"
        SMALL = "2_5", "2–5 people"
        MEDIUM = "6_15", "6–15 people"
        LARGE = "16_plus", "16+ people"

    class Contact(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        CALL = "call", "Phone call"
        EMAIL = "email", "E-mail"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        DEMO = "demo", "Demo scheduled"
        PROPOSAL = "proposal", "Proposal sent"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    name = models.CharField(max_length=100)
    studio_name = models.CharField("Studio / company", max_length=120, blank=True)
    mobile = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=60, blank=True)
    team_size = models.CharField(max_length=10, choices=TeamSize.choices, blank=True)
    modules = models.JSONField("Interested in", default=list, blank=True)
    contact_pref = models.CharField("Preferred contact", max_length=10, choices=Contact.choices, default=Contact.WHATSAPP)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    notes = models.TextField("Internal notes", blank=True)
    source = models.CharField(max_length=40, default="landing")
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Product enquiry"
        verbose_name_plural = "Product enquiries"

    def __str__(self):
        return f"{self.name} — {self.studio_name or self.city or self.mobile}"

    @property
    def modules_display(self):
        from .modules import MODULES
        labels = {k: label for k, label, _, _ in MODULES} | {"complete": "Complete system", "not_sure": "Not sure yet"}
        return ", ".join(labels.get(m, m) for m in self.modules) or "—"


class DemoLink(models.Model):
    """A personal demo link for one prospect: the demo shows their business name (and logo/colour) and every
    open, page and click is recorded, so sales knows who looked at the demo and what they cared about."""

    business_name = models.CharField(max_length=120, help_text="Shown everywhere in the demo, e.g. Sharma Interiors.")
    contact_name = models.CharField("Contact person", max_length=100, blank=True,
                                    help_text="Optional. Used in the welcome message: “Welcome, Rahul!”")
    mobile = models.CharField("Mobile / WhatsApp", max_length=15, blank=True,
                              help_text="Optional. 10-digit number, for the “Send on WhatsApp” button.")
    city = models.CharField(max_length=80, blank=True, help_text="Optional. Replaces the demo city.")
    logo = models.ImageField(upload_to="demo_links/", blank=True,
                             help_text="Optional. The brand colours are picked from the logo.")
    accent_color = models.CharField("Brand colour", max_length=7, blank=True, validators=[hex_color],
                                    help_text="Optional, e.g. #B5651D. Leave empty to pick it from the logo.")
    secondary_color = models.CharField(max_length=7, blank=True, editable=False)
    dark_color = models.CharField(max_length=7, blank=True, editable=False)
    slug = models.SlugField("Link name", max_length=80, unique=True, blank=True,
                            help_text="The end of the link (…/d/<link name>/). Leave empty to make it from the business name.")
    enquiry = models.ForeignKey("ProductEnquiry", on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="demo_links", help_text="Optional: the enquiry this link was made for.")
    notes = models.TextField("Internal notes", blank=True)
    is_active = models.BooleanField("Link works", default=True,
                                    help_text="Untick to switch the link off (it then opens the normal demo).")
    created_at = models.DateTimeField(auto_now_add=True)
    first_opened_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    visits = models.PositiveIntegerField(default=0, help_text="Separate visits (30 minutes apart).")
    page_views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Client demo link"

    def __str__(self):
        return self.business_name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("core:demo_link", args=[self.slug])

    def save(self, *args, **kwargs):
        from django.utils.text import slugify

        from .branding import DEFAULT, palette_from_color, palette_from_logo
        if not self.slug:
            base = slugify(self.business_name)[:70] or "studio"
            slug, n = base, 2
            while DemoLink.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        if self.accent_color:
            self.accent_color, self.secondary_color, self.dark_color = palette_from_color(self.accent_color)
        elif self.logo:
            try:
                colours = palette_from_logo(self.logo.file)
                self.logo.file.seek(0)
            except Exception:
                colours = DEFAULT
            if colours != DEFAULT:
                self.accent_color, self.secondary_color, self.dark_color = colours
        else:
            self.secondary_color = self.dark_color = ""
        super().save(*args, **kwargs)


class DemoVisit(models.Model):
    """One thing a prospect did on their demo link: opened it, viewed a page, or clicked something."""

    class Kind(models.TextChoices):
        OPEN = "open", "Opened the link"
        PAGE = "page", "Viewed a page"
        ACTION = "action", "Clicked"

    link = models.ForeignKey(DemoLink, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.PAGE)
    path = models.CharField(max_length=300, blank=True)
    title = models.CharField(max_length=160, blank=True)
    device = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demo link activity"
        verbose_name_plural = "Demo link activity"

    def __str__(self):
        return f"{self.link} · {self.get_kind_display()} · {self.title or self.path}"
