import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.images import get_image_dimensions
from django.core.validators import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class FileValidator:
    allowed_extensions = [".jpg", ".jpeg", ".png"]
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


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """

    email = models.EmailField(_("email address"), unique=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)

    # Login attempt tracking
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username

    def full_name(self):
        """
        Returns the user's full name
        """
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def role(self):
        """
        Returns the user's role from the associated UserProfile
        """
        try:
            return self.userprofile.role
        except:
            return "team_member"

    def is_admin(self):
        # Check both profile role and Django admin status for security
        if self.is_superuser or self.is_staff:
            return True
        return hasattr(self, "userprofile") and self.userprofile.role == "admin"

    def is_project_manager(self):
        return (
            hasattr(self, "userprofile") and self.userprofile.role == "project_manager"
        )

    def is_team_member(self):
        return hasattr(self, "userprofile") and self.userprofile.role == "team_member"

    def is_leader(self):
        return hasattr(self, "userprofile") and self.userprofile.role == "leader"

    def is_account_locked(self):
        """Check if account is currently locked due to failed login attempts"""
        if self.account_locked_until and timezone.now() < self.account_locked_until:
            return True
        return False

    def reset_failed_attempts(self):
        """Reset failed login attempts after successful login"""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.account_locked_until = None
        self.save(
            update_fields=[
                "failed_login_attempts",
                "last_failed_login",
                "account_locked_until",
            ]
        )

    def increment_failed_attempts(self):
        """Increment failed login attempts and lock account if needed"""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()

        if self.failed_login_attempts >= 3:
            self.account_locked_until = timezone.now() + timedelta(minutes=30)

        self.save(
            update_fields=[
                "failed_login_attempts",
                "last_failed_login",
                "account_locked_until",
            ]
        )

    def get_lockout_time_remaining(self):
        """Get remaining lockout time in minutes"""
        if self.account_locked_until and timezone.now() < self.account_locked_until:
            remaining = self.account_locked_until - timezone.now()
            return int(remaining.total_seconds() / 60)
        return 0


class UserProfile(models.Model):
    """
    Extended profile for User model with role-based attributes
    """

    # Role constants
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    TEAM_MEMBER = "team_member"
    LEADER = "leader"

    ROLE_CHOICES = (
        (ADMIN, _("Admin")),
        (PROJECT_MANAGER, _("Project Manager")),
        (TEAM_MEMBER, _("Team Member")),
        (LEADER, _("Leader")),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=TEAM_MEMBER)
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        validators=[FileValidator()],
        help_text="Allowed formats: JPG, PNG. Max size: 5MB",
    )
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
