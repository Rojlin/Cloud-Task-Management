from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class ChatRoom(models.Model):
    """
    Model for chat rooms
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='created_chat_rooms'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chat_rooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    
    @property
    def get_last_message(self):
        return self.messages.order_by('-created_at').first()

class ChatMessage(models.Model):
    """
    Model for individual chat messages
    """
    room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"Message from {self.sender.username} in {self.room.name}"
