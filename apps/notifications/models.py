from django.db import models
from django.conf import settings

class Notification(models.Model):
    """
    Model for user notifications
    """
    # Types of notifications
    NOTIFICATION_TYPES = (
        ('task_assigned', 'Task Assigned'),
        ('task_updated', 'Task Updated'),
        ('task_commented', 'Task Commented'),
        ('project_created', 'Project Created'),
        ('project_updated', 'Project Updated'),
        ('project_member_added', 'Project Member Added'),
        ('chat_message', 'Chat Message'),
        ('system', 'System Notification'),
        ('user_verified', 'User Verified'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    link = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='system')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} for {self.user.username}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()
