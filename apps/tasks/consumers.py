import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from .models import Task, TaskComment, TaskAttachment
from apps.notifications.models import Notification

User = get_user_model()

class TaskConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time task updates
    """
    
    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection
        """
        self.user = self.scope["user"]
        
        # Reject connection if user is not authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Accept connection
        await self.accept()
        
        # Add this channel to task updates group
        self.task_group_name = 'task_updates'
        await self.channel_layer.group_add(
            self.task_group_name,
            self.channel_name
        )
    
    async def disconnect(self, close_code):
        """
        Called when the WebSocket closes for any reason
        """
        # Remove this channel from the task group
        if hasattr(self, 'task_group_name'):
            await self.channel_layer.group_discard(
                self.task_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Called when we get a message from the client
        """
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            
            if action == 'update_task':
                task_id = text_data_json.get('task_id')
                status = text_data_json.get('status')
                # Update task and notify all connected clients
                await self.update_task(task_id, status)
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))
    
    @database_sync_to_async
    def update_task(self, task_id, status):
        """
        Update a task's status
        """
        task = Task.objects.get(id=task_id)
        
        # Check if user has permission to update this task
        if self.user.is_admin or task.created_by == self.user or task.assigned_to == self.user:
            task.status = status
            task.save()
            
            # Send task update to all clients
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'task_updates',
                {
                    'type': 'task_update',
                    'task': {
                        'id': task.id,
                        'title': task.title,
                        'status': task.status,
                        'updated_by': self.user.username
                    }
                }
            )
    
    async def task_update(self, event):
        """
        Handler for task.update type events
        """
        # Send a task update to the WebSocket
        await self.send(text_data=json.dumps({
            'task_update': True,
            'task': event['task']
        }))

class TaskCommentsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for task comments and updates
    """
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        # Get task ID from the URL
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.task_group_name = f'task_{self.task_id}'
        
        # Add the user to the group for this task
        await self.channel_layer.group_add(
            self.task_group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        
        # Send initial task data
        task_data = await self.get_task_data()
        if task_data:
            await self.send(text_data=json.dumps({
                'type': 'initial_data',
                'task': task_data
            }))
        
    async def disconnect(self, close_code):
        # Remove the user from the task group
        await self.channel_layer.group_discard(
            self.task_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handle received data from the WebSocket
        """
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'comment':
            # Handle new comment
            comment = data.get('comment', '')
            comment_obj = await self.save_comment(comment)
            
            # Broadcast the comment to all users in the group
            await self.channel_layer.group_send(
                self.task_group_name,
                {
                    'type': 'task_comment',
                    'comment': {
                        'id': comment_obj.id,
                        'content': comment_obj.comment,
                        'created_at': comment_obj.created_at.isoformat(),
                        'user': {
                            'id': comment_obj.user.id,
                            'username': comment_obj.user.username,
                            'full_name': comment_obj.user.get_full_name() or comment_obj.user.username
                        }
                    }
                }
            )
            
            # Create notification for task assignee if not the commenter
            await self.create_comment_notification(comment_obj)
            
        elif message_type == 'status_update':
            # Handle status update
            status = data.get('status')
            await self.update_task_status(status)
            
            # Broadcast the status update
            await self.channel_layer.group_send(
                self.task_group_name,
                {
                    'type': 'task_status_update',
                    'status': status,
                    'updated_by': self.user.username
                }
            )
            
            # Create notification for task owner
            await self.create_status_update_notification(status)
            
        elif message_type == 'priority_update':
            # Handle priority update
            priority = data.get('priority')
            await self.update_task_priority(priority)
            
            # Broadcast the priority update
            await self.channel_layer.group_send(
                self.task_group_name,
                {
                    'type': 'task_priority_update',
                    'priority': priority,
                    'updated_by': self.user.username
                }
            )
            
            # Create notification for task owner
            await self.create_priority_update_notification(priority)
    
    async def task_comment(self, event):
        """
        Send task comment to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'new_comment',
            'comment': event['comment']
        }))
    
    async def task_status_update(self, event):
        """
        Send task status update to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': event['status'],
            'updated_by': event['updated_by']
        }))
    
    async def task_priority_update(self, event):
        """
        Send task priority update to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'priority_update',
            'priority': event['priority'],
            'updated_by': event['updated_by']
        }))
    
    @database_sync_to_async
    def get_task_data(self):
        """
        Get task data in a format suitable for JSON
        """
        try:
            task = Task.objects.get(pk=self.task_id)
            comments = TaskComment.objects.filter(task=task).order_by('created_at')
            attachments = TaskAttachment.objects.filter(task=task).order_by('uploaded_at')
            
            comments_data = [{
                'id': comment.id,
                'comment': comment.comment,
                'content': comment.comment,  # Keep content for backward compatibility
                'created_at': comment.created_at.isoformat(),
                'user': {
                    'id': comment.user.id,
                    'username': comment.user.username,
                    'full_name': comment.user.get_full_name() or comment.user.username
                }
            } for comment in comments]
            
            attachments_data = [{
                'id': attachment.id,
                'file_name': attachment.file.name.split('/')[-1],
                'url': attachment.file.url,
                'created_at': attachment.created_at.isoformat(),
                'user': {
                    'id': attachment.user.id,
                    'username': attachment.user.username,
                    'full_name': attachment.user.get_full_name() or attachment.user.username
                }
            } for attachment in attachments]
            
            return {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'created_by': {
                    'id': task.created_by.id,
                    'username': task.created_by.username,
                    'full_name': task.created_by.get_full_name() or task.created_by.username
                },
                'assigned_to': {
                    'id': task.assigned_to.id,
                    'username': task.assigned_to.username,
                    'full_name': task.assigned_to.get_full_name() or task.assigned_to.username
                } if task.assigned_to else None,
                'comments': comments_data,
                'attachments': attachments_data,
            }
        except Task.DoesNotExist:
            return None
    
    @database_sync_to_async
    def save_comment(self, comment_text):
        """
        Save a new comment to the database
        """
        task = Task.objects.get(pk=self.task_id)
        comment = TaskComment.objects.create(
            task=task,
            user=self.user,
            comment=comment_text
        )
        return comment
    
    @database_sync_to_async
    def update_task_status(self, status):
        """
        Update task status
        """
        task = Task.objects.get(pk=self.task_id)
        task.status = status
        task.save(update_fields=['status'])
        return task
    
    @database_sync_to_async
    def update_task_priority(self, priority):
        """
        Update task priority
        """
        task = Task.objects.get(pk=self.task_id)
        task.priority = priority
        task.save(update_fields=['priority'])
        return task
    
    @database_sync_to_async
    def create_comment_notification(self, comment):
        """
        Create notification for task assignee when a new comment is added
        """
        task = comment.task
        if task.assigned_to and task.assigned_to != self.user:
            Notification.objects.create(
                user=task.assigned_to,
                title=f"New comment on task: {task.title}",
                message=f"{self.user.username}: {comment.comment[:50]}...",
                link=f"/tasks/{task.id}/",
                notification_type='task_comment'
            )
    
    @database_sync_to_async
    def create_status_update_notification(self, status):
        """
        Create notification for task owner when status is updated
        """
        task = Task.objects.get(pk=self.task_id)
        
        # Notify the task creator if not the same as the updater
        if task.created_by != self.user:
            status_display = dict(Task.STATUS_CHOICES).get(status, status)
            Notification.objects.create(
                user=task.created_by,
                title=f"Task status updated: {task.title}",
                message=f"{self.user.username} changed status to {status_display}",
                link=f"/tasks/{task.id}/",
                notification_type='task_update'
            )
        
        # Also notify assignee if different from creator and updater
        if task.assigned_to and task.assigned_to != task.created_by and task.assigned_to != self.user:
            status_display = dict(Task.STATUS_CHOICES).get(status, status)
            Notification.objects.create(
                user=task.assigned_to,
                title=f"Task status updated: {task.title}",
                message=f"{self.user.username} changed status to {status_display}",
                link=f"/tasks/{task.id}/",
                notification_type='task_update'
            )
    
    @database_sync_to_async
    def create_priority_update_notification(self, priority):
        """
        Create notification for task owner when priority is updated
        """
        task = Task.objects.get(pk=self.task_id)
        
        # Notify the task creator if not the same as the updater
        if task.created_by != self.user:
            priority_display = dict(Task.PRIORITY_CHOICES).get(priority, priority)
            Notification.objects.create(
                user=task.created_by,
                title=f"Task priority updated: {task.title}",
                message=f"{self.user.username} changed priority to {priority_display}",
                link=f"/tasks/{task.id}/",
                notification_type='task_update'
            )
        
        # Also notify assignee if different from creator and updater
        if task.assigned_to and task.assigned_to != task.created_by and task.assigned_to != self.user:
            priority_display = dict(Task.PRIORITY_CHOICES).get(priority, priority)
            Notification.objects.create(
                user=task.assigned_to,
                title=f"Task priority updated: {task.title}",
                message=f"{self.user.username} changed priority to {priority_display}",
                link=f"/tasks/{task.id}/",
                notification_type='task_update'
            )