import os

from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.core.validators import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from apps.projects.models import Project


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


class Task(models.Model):
    """
    Task model to represent a task in the task management system
    """

    # Status Choices
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"

    STATUS_CHOICES = (
        (TODO, _("To Do")),
        (IN_PROGRESS, _("In Progress")),
        (REVIEW, _("In Review")),
        (COMPLETED, _("Completed")),
    )

    # Priority Choices
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    PRIORITY_CHOICES = (
        (LOW, _("Low")),
        (MEDIUM, _("Medium")),
        (HIGH, _("High")),
        (URGENT, _("Urgent")),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=TODO)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=MEDIUM)
    due_date = models.DateField()

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_tasks"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("tasks:detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        # If status changed to completed, set completed_at
        if self.pk:
            old_task = Task.objects.get(pk=self.pk)
            if old_task.status != self.status and self.status == self.COMPLETED:
                self.completed_at = timezone.now()
            elif old_task.status == self.COMPLETED and self.status != self.COMPLETED:
                self.completed_at = None

            # Check if due date has changed and is now approaching
            from django.urls import reverse

            from apps.notifications.models import Notification

            # Only check for non-completed tasks
            if self.status != self.COMPLETED:
                today = timezone.now().date()
                days_threshold = (
                    3  # Configure the days threshold for approaching deadlines
                )

                # If due date is within threshold and has been changed
                if (
                    self.due_date != old_task.due_date
                    and self.due_date > today
                    and (self.due_date - today).days <= days_threshold
                ):

                    days_left = (self.due_date - today).days

                    # Create notifications for assigned user
                    if self.assigned_to:
                        Notification.objects.create(
                            user=self.assigned_to,
                            title="Task Due Date Updated",
                            message=f'Task "{self.title}" is now due in {days_left} day{"s" if days_left != 1 else ""}.',
                            link=reverse("tasks:detail", kwargs={"pk": self.id}),
                        )

                    # Create notification for task creator if different from assigned user
                    if self.created_by and self.created_by != self.assigned_to:
                        Notification.objects.create(
                            user=self.created_by,
                            title="Task Due Date Updated",
                            message=f'Task "{self.title}" is now due in {days_left} day{"s" if days_left != 1 else ""}.',
                            link=reverse("tasks:detail", kwargs={"pk": self.id}),
                        )

        elif self.status == self.COMPLETED:
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_completed(self):
        return self.status == self.COMPLETED

    @property
    def is_overdue(self):
        return not self.is_completed and self.due_date < timezone.now().date()

    @property
    def days_left(self):
        if self.is_completed:
            return 0
        if self.due_date < timezone.now().date():
            return 0
        return (self.due_date - timezone.now().date()).days


class TaskComment(models.Model):
    """
    Comment model for tasks
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = (
        models.TextField()
    )  # Changed from content to comment to match database schema
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.task.title}"


def task_attachment_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/task_<id>/<filename>
    return f"task_{instance.task.id}/{filename}"


class TaskAttachment(models.Model):
    """
    Attachment model for task files
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        upload_to=task_attachment_path,
        validators=[FileValidator()],
        help_text="Allowed formats: JPG, PNG, DOC, DOCX, XLS, XLSX. Max size: 5MB",
    )
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Attachment for {self.task.title}"

    @property
    def file_name(self):
        return os.path.basename(self.file.name)

    @property
    def file_extension(self):
        return os.path.splitext(self.file.name)[1].lower()
