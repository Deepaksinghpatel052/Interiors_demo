from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.validators import validate_document, validate_image
from website.models import PropertyType

User = settings.AUTH_USER_MODEL


class ClientProject(models.Model):
    class Stage(models.TextChoices):
        DESIGN = "design", "Design"
        APPROVAL = "approval", "Client approval"
        ORDERING = "ordering", "Material ordering"
        EXECUTION = "execution", "Execution"
        HANDOVER = "handover", "Handover"
        COMPLETED = "completed", "Completed"

    code = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=140)
    lead = models.OneToOneField("crm.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="project")
    client = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="client_projects")
    client_name = models.CharField(max_length=100)
    client_mobile = models.CharField(max_length=15, blank=True)
    client_email = models.EmailField(blank=True)
    designer = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="designed_projects")
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.DESIGN)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices, blank=True)
    site_address = models.CharField(max_length=240, blank=True)
    area_sqft = models.PositiveIntegerField(default=0)
    start_date = models.DateField(default=timezone.localdate)
    target_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                      help_text="Spend so far on materials and labour.")
    notes = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "-created_at"]

    def __str__(self):
        return f"{self.code} · {self.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            year = (self.start_date or timezone.localdate()).year
            n = ClientProject.objects.filter(code__startswith=f"PRJ-{year}-").count() + 1
            while ClientProject.objects.filter(code=f"PRJ-{year}-{n:03d}").exists():
                n += 1
            self.code = f"PRJ-{year}-{n:03d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("studio:project_detail", args=[self.pk])

    @property
    def progress(self):
        ms = list(self.milestones.all())
        if not ms:
            return 0
        return round(100 * sum(m.status == Milestone.Status.DONE for m in ms) / len(ms))

    @property
    def next_milestone(self):
        return self.milestones.exclude(status=Milestone.Status.DONE).order_by("order", "due_date").first()

    @property
    def budget_used_pct(self):
        return round(100 * float(self.actual_cost) / float(self.budget)) if self.budget else 0


class ProjectSpace(models.Model):
    project = models.ForeignKey(ClientProject, related_name="spaces", on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    area_sqft = models.PositiveIntegerField(default=0)
    scope = models.CharField(max_length=240, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class Milestone(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    project = models.ForeignKey(ClientProject, related_name="milestones", on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_on = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "due_date", "id"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return self.status != self.Status.DONE and self.due_date and self.due_date < timezone.localdate()


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        DOING = "doing", "In progress"
        DONE = "done", "Done"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"

    project = models.ForeignKey(ClientProject, related_name="tasks", on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    from_client = models.BooleanField(default=False, help_text="Raised by the client from the portal.")
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_date", "-priority", "id"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return self.status != self.Status.DONE and self.due_date and self.due_date < timezone.localdate()


class DesignProposal(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SHARED = "shared", "Shared with client"
        APPROVED = "approved", "Approved"
        CHANGES = "changes", "Changes requested"

    project = models.ForeignKey(ClientProject, related_name="proposals", on_delete=models.CASCADE)
    version = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=140)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    shared_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_comment = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["project", "version"], name="unique_proposal_version")]

    def __str__(self):
        return f"v{self.version} · {self.title}"


class ProposalImage(models.Model):
    proposal = models.ForeignKey(DesignProposal, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="proposals/", validators=[validate_image])
    caption = models.CharField(max_length=140, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class ProposalComment(models.Model):
    proposal = models.ForeignKey(DesignProposal, related_name="comments", on_delete=models.CASCADE)
    image = models.ForeignKey(ProposalImage, null=True, blank=True, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    text = models.TextField(max_length=1500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class SiteUpdate(models.Model):
    project = models.ForeignKey(ClientProject, related_name="updates", on_delete=models.CASCADE)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    message = models.TextField(max_length=2000)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]


class SiteUpdatePhoto(models.Model):
    update = models.ForeignKey(SiteUpdate, related_name="photos", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="site_updates/", validators=[validate_image])


class ProjectDocument(models.Model):
    class Kind(models.TextChoices):
        AGREEMENT = "agreement", "Agreement"
        DRAWING = "drawing", "Drawing"
        OTHER = "other", "Other"

    project = models.ForeignKey(ClientProject, related_name="documents", on_delete=models.CASCADE)
    title = models.CharField(max_length=140)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    file = models.FileField(upload_to="documents/", validators=[validate_document])
    visible_to_client = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ClientRequest(models.Model):
    """A request or snag raised by the client from the portal; becomes a task."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"

    project = models.ForeignKey(ClientProject, related_name="requests", on_delete=models.CASCADE)
    raised_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=140)
    description = models.TextField(max_length=2000, blank=True)
    photo = models.ImageField(upload_to="requests/", blank=True, validators=[validate_image])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    task = models.OneToOneField(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name="client_request")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
