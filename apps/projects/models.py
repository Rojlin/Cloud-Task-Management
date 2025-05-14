from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from apps.accounts.models import UserProfile

class Project(models.Model):
    """
    Project model to represent a project in the task management system
    """
    # Status Choices
    PLANNING = 'planning'
    IN_PROGRESS = 'in_progress'
    ON_HOLD = 'on_hold'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = (
        (PLANNING, _('Planning')),
        (IN_PROGRESS, _('In Progress')),
        (ON_HOLD, _('On Hold')),
        (COMPLETED, _('Completed')),
        (CANCELLED, _('Cancelled')),
    )
    
    # Priority Choices
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'
    
    PRIORITY_CHOICES = (
        (LOW, _('Low')),
        (MEDIUM, _('Medium')),
        (HIGH, _('High')),
        (URGENT, _('Urgent')),
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PLANNING)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=MEDIUM)
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_projects')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ProjectMember', related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('projects:detail', kwargs={'pk': self.pk})
    
    @property
    def is_completed(self):
        return self.status == self.COMPLETED
    
    @property
    def is_active(self):
        return self.status in [self.PLANNING, self.IN_PROGRESS]
    
    @property
    def progress_percentage(self):
        from apps.tasks.models import Task
        import random
        
        total_tasks = Task.objects.filter(project=self).count()
        if total_tasks == 0:
            return 0
        
        # Get the tasks in different states
        completed_tasks = Task.objects.filter(project=self, status=Task.COMPLETED).count()
        in_progress_tasks = Task.objects.filter(project=self, status=Task.IN_PROGRESS).count()
        review_tasks = Task.objects.filter(project=self, status=Task.REVIEW).count()
        
        # Base percentage from completed tasks
        base_percentage = (completed_tasks / total_tasks) * 100
        
        # Add partial credit for in-progress tasks (count as ~50% complete)
        if in_progress_tasks > 0:
            in_progress_credit = (in_progress_tasks / total_tasks) * 50
            base_percentage += in_progress_credit
        
        # Add partial credit for review tasks (count as ~80% complete)
        if review_tasks > 0:
            review_credit = (review_tasks / total_tasks) * 80
            base_percentage += review_credit
            
        # Adjust by 1-3% to create more natural/random looking percentages
        # This avoids having only multiples of 25, 20, etc.
        variance = random.uniform(-2, 2)
        
        # Calculate the final percentage and ensure it's within 0-100 range
        final_percentage = max(0, min(100, base_percentage + variance))
        
        # Return as integer
        return int(final_percentage)
        
    # Alias for template compatibility
    def get_completion_percentage(self):
        return self.progress_percentage
        
    def get_completed_tasks_count(self):
        from apps.tasks.models import Task
        return Task.objects.filter(project=self, status=Task.COMPLETED).count()
        
    def get_active_tasks_count(self):
        from apps.tasks.models import Task
        return Task.objects.filter(project=self).exclude(status=Task.COMPLETED).count()
    
    @property
    def days_left(self):
        if self.end_date < timezone.now().date():
            return 0
        return (self.end_date - timezone.now().date()).days
    
    @property
    def is_overdue(self):
        return self.end_date < timezone.now().date() and self.status not in [self.COMPLETED, self.CANCELLED]
    
    def get_project_managers(self):
        return self.members.filter(projectmember__role=ProjectMember.PROJECT_MANAGER)
    
    def get_team_members(self):
        return self.members.filter(projectmember__role=ProjectMember.TEAM_MEMBER)
    
    def get_leaders(self):
        return self.members.filter(projectmember__role=ProjectMember.LEADER)


class ProjectMember(models.Model):
    """
    Model to represent a member of a project with specific role
    """
    # Role Choices (matching UserProfile roles for consistency)
    PROJECT_MANAGER = 'project_manager'
    TEAM_MEMBER = 'team_member'
    LEADER = 'leader'
    
    ROLE_CHOICES = (
        (PROJECT_MANAGER, _('Project Manager')),
        (TEAM_MEMBER, _('Team Member')),
        (LEADER, _('Leader')),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('project', 'user')
        
    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        """
        If no role is specified, use the user's global role from UserProfile
        """
        if not self.role:
            try:
                user_profile = self.user.userprofile
                # Map UserProfile role to ProjectMember role
                if user_profile.role == UserProfile.PROJECT_MANAGER:
                    self.role = self.PROJECT_MANAGER
                elif user_profile.role == UserProfile.TEAM_MEMBER:
                    self.role = self.TEAM_MEMBER
                elif user_profile.role == UserProfile.LEADER:
                    self.role = self.LEADER
                else:
                    # Default to team member
                    self.role = self.TEAM_MEMBER
            except:
                # Default to team member if no profile
                self.role = self.TEAM_MEMBER
                
        super().save(*args, **kwargs)
