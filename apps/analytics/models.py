import os

from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.core.validators import ValidationError
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from apps.projects.models import Project
from apps.tasks.models import Task


@deconstructible
class FileValidator:
    allowed_extensions = [".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx"]
    max_size = 5 * 1024 * 1024  # 5MB

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, value):
        # Check file extension
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(
                f'Unsupported file extension. Allowed extensions: {", ".join(self.allowed_extensions)}'
            )

        # Check file size
        if value.size > self.max_size:
            raise ValidationError(
                f"File size too large. Maximum allowed size is {self.max_size/1024/1024}MB"
            )

        # Additional check for image files (width/height if needed)
        if ext in [".jpg", ".jpeg", ".png"]:
            try:
                width, height = get_image_dimensions(value)
                if not width or not height:
                    raise ValidationError("Invalid image file")
            except Exception as e:
                raise ValidationError("Invalid image file")


class ReportType(models.Model):
    """
    Model for different report types that can be generated
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Report(models.Model):
    """
    Model for storing generated reports
    """

    FREQUENCY_CHOICES = (
        ("once", _("One-time")),
        ("daily", _("Daily")),
        ("weekly", _("Weekly")),
        ("monthly", _("Monthly")),
        ("quarterly", _("Quarterly")),
    )

    FORMAT_CHOICES = (
        ("pdf", _("PDF")),
        ("excel", _("Excel")),
        ("csv", _("CSV")),
        ("json", _("JSON")),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.ForeignKey(
        ReportType, on_delete=models.CASCADE, related_name="reports"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="reports", null=True, blank=True
    )
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default="pdf")
    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES, default="once"
    )
    last_generated = models.DateTimeField(null=True, blank=True)
    next_generation = models.DateTimeField(null=True, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ReportFile(models.Model):
    """
    Model for storing generated report files
    """

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(
        upload_to="reports/",
        validators=[FileValidator()],
        help_text="Allowed formats: JPG, PNG, DOC, DOCX, XLS, XLSX. Max size: 5MB",
    )
    format = models.CharField(max_length=10, choices=Report.FORMAT_CHOICES)
    size = models.IntegerField(help_text=_("File size in bytes"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report.title} - {self.created_at.strftime('%Y-%m-%d')}"


class AnalyticsSnapshot(models.Model):
    """
    Model for storing periodic analytics data snapshots
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="analytics_snapshots",
        null=True,
        blank=True,
    )
    total_tasks = models.IntegerField(default=0)
    completed_tasks = models.IntegerField(default=0)
    pending_tasks = models.IntegerField(default=0)
    overdue_tasks = models.IntegerField(default=0)
    avg_completion_time = models.DurationField(null=True, blank=True)
    active_users = models.IntegerField(default=0)
    data_json = models.JSONField(
        default=dict, blank=True, help_text=_("Additional analytics data")
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        project_name = self.project.name if self.project else "All Projects"
        return f"Analytics for {project_name} on {self.timestamp.strftime('%Y-%m-%d')}"


class UserProductivity(models.Model):
    """
    Model for tracking individual user productivity
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="productivity_metrics",
    )
    date = models.DateField()
    tasks_assigned = models.IntegerField(default=0)
    tasks_completed = models.IntegerField(default=0)
    tasks_created = models.IntegerField(default=0)
    comments_added = models.IntegerField(default=0)
    avg_response_time = models.DurationField(null=True, blank=True)
    activity_score = models.FloatField(default=0)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"Productivity for {self.user.username} on {self.date}"


class TaskCompletionTime(models.Model):
    """
    Model for tracking task completion time analytics
    """

    task = models.OneToOneField(
        Task, on_delete=models.CASCADE, related_name="completion_time"
    )
    assigned_date = models.DateTimeField()
    start_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField()
    time_to_start = models.DurationField(null=True, blank=True)
    time_to_complete = models.DurationField()
    expected_time = models.DurationField(null=True, blank=True)
    time_difference = models.DurationField(null=True, blank=True)
    efficiency_score = models.FloatField(default=0)

    def __str__(self):
        return f"Completion Time for {self.task.title}"
