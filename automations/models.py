from django.db import models


class Automation(models.TextChoices):
    BOOKING_CONFIRMATION = "booking_confirmation", "Booking confirmation"
    CONSULTATION_REMINDER = "consultation_reminder", "Reminder 1 day before a consultation"
    QUOTATION_SENT = "quotation_sent", "“Quotation sent” notification"
    PAYMENT_DUE = "payment_due", "Payment due reminder"
    NEW_LEAD = "new_lead", "New lead alert to the owner"
    LEAD_FOLLOWUP = "lead_followup", "Follow-up reminder for untouched leads"


class MessageTemplate(models.Model):
    key = models.CharField(max_length=40, choices=Automation.choices, unique=True)
    body = models.TextField(help_text="Placeholders in {curly braces} are filled in automatically.")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.get_key_display()


class AutomationLog(models.Model):
    class Status(models.TextChoices):
        SIMULATED = "simulated", "Prepared (demo — not sent)"

    automation = models.CharField(max_length=40, choices=Automation.choices)
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=15, blank=True)
    to_owner = models.BooleanField(default=False)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SIMULATED)
    lead = models.ForeignKey("crm.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="automation_logs")
    booking = models.ForeignKey("bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    project = models.ForeignKey("studio.ClientProject", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    invoice = models.ForeignKey("finance.Invoice", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    quotation = models.ForeignKey("finance.Quotation", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_automation_display()} → {self.recipient_name}"
