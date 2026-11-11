from django.conf import settings
from django.db import models

from website.models import BudgetBand, PropertyType


class Lead(models.Model):
    class Stage(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        CONSULTATION = "consultation", "Consultation"
        SITE_VISIT = "site_visit", "Site visit"
        PROPOSAL = "proposal", "Proposal sent"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    class Source(models.TextChoices):
        WEBSITE = "website", "Website"
        INSTAGRAM = "instagram", "Instagram"
        REFERRAL = "referral", "Referral"
        WALK_IN = "walk_in", "Walk-in"
        AI = "ai_assistant", "AI assistant"
        ESTIMATOR = "cost_estimator", "Cost estimator"

    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=60, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WEBSITE)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices, blank=True)
    budget_band = models.CharField(max_length=20, choices=BudgetBand.choices, blank=True)
    style_preference = models.CharField(max_length=60, blank=True)
    message = models.TextField(blank=True)
    estimate = models.JSONField(blank=True, null=True)
    notes = models.TextField(blank=True)
    follow_up_date = models.DateField(blank=True, null=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="leads")
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_stage_display()})"


class LeadActivity(models.Model):
    lead = models.ForeignKey(Lead, related_name="activities", on_delete=models.CASCADE)
    text = models.CharField(max_length=300)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Lead activities"
