from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    email = models.EmailField(_('email address'), unique=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.username

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def role(self):
        """
        Returns the user's role from the associated UserProfile
        """
        try:
            return self.userprofile.role
        except:
            return None
            
    @property
    def is_admin(self):
        return self.is_superuser or (hasattr(self, 'userprofile') and self.userprofile.role == UserProfile.ADMIN)
    
    @property
    def is_project_manager(self):
        return hasattr(self, 'userprofile') and self.userprofile.role == UserProfile.PROJECT_MANAGER
    
    @property
    def is_team_member(self):
        return hasattr(self, 'userprofile') and self.userprofile.role == UserProfile.TEAM_MEMBER
    
    @property
    def is_leader(self):
        return hasattr(self, 'userprofile') and self.userprofile.role == UserProfile.LEADER


class UserProfile(models.Model):
    """
    Extended profile for User model with role-based attributes
    """
    # Role choices
    ADMIN = 'admin'
    PROJECT_MANAGER = 'project_manager'
    TEAM_MEMBER = 'team_member'
    LEADER = 'leader'
    
    ROLE_CHOICES = (
        (ADMIN, _('Admin')),
        (PROJECT_MANAGER, _('Project Manager')),
        (TEAM_MEMBER, _('Team Member')),
        (LEADER, _('Leader')),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=TEAM_MEMBER)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
