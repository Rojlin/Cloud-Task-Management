import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Count
from django.utils import timezone


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications
    """

    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection
        """
        self.user = self.scope["user"]

        # Accept connection for all users, we'll handle non-authenticated users differently
        await self.accept()

        # If not authenticated, send a message indicating they need to authenticate
        if not self.user.is_authenticated:
            print(f"User not authenticated, sending auth required message")
            await self.send(
                text_data=json.dumps(
                    {"error": "Authentication required", "authenticated": False}
                )
            )
            return

        # Add this channel to a user-specific notification group
        self.notification_group_name = f"notifications_{self.user.id}"

        # Debug information
        print(
            f"Adding user {self.user.id} ({self.user.username}) to notification group: {self.notification_group_name}"
        )

        await self.channel_layer.group_add(
            self.notification_group_name, self.channel_name
        )

        # Send initial unread count
        await self.send_unread_count()

    async def disconnect(self, close_code):
        """
        Called when the WebSocket closes for any reason
        """
        # Remove this channel from the notification group
        if hasattr(self, "notification_group_name"):
            await self.channel_layer.group_discard(
                self.notification_group_name, self.channel_name
            )

    async def receive(self, text_data):
        """
        Called when we get a message from the client
        """
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get("action")

            if action == "get_count":
                await self.send_unread_count()
            elif action == "mark_all_read":
                await self.mark_all_read()
                await self.send_unread_count()
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))

    @database_sync_to_async
    def get_unread_count(self):
        """
        Get the count of unread notifications for the current user
        """
        from .models import Notification

        return Notification.objects.filter(user=self.user, is_read=False).count()

    @database_sync_to_async
    def mark_all_read(self):
        """
        Mark all notifications for the current user as read
        """
        from .models import Notification

        Notification.objects.filter(user=self.user, is_read=False).update(is_read=True)

    async def send_unread_count(self):
        """
        Send the unread notification count to the client
        """
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({"unread_count": count}))

    async def notification_message(self, event):
        """
        Handler for notification_message type events
        """
        # Debug notification received
        print(
            f"NotificationConsumer received notification_message event for user {self.user.id}"
        )
        print(f"Notification data: {event}")

        # Check if the notification is in the old format (with 'notification') or new format (with 'message')
        notification_data = {}
        if "notification" in event:
            notification_data = event["notification"]
        elif "message" in event:
            notification_data = {
                "id": 0,  # We don't need the actual ID for display
                "title": event["message"].get("title", "New Notification"),
                "message": event["message"].get("content", ""),
                "is_read": False,
                "created_at": timezone.now().isoformat(),
                "link": event["message"].get("link", "#"),
            }

        # Get the unread count
        unread_count = await self.get_unread_count()

        # Send a notification to the WebSocket
        await self.send(
            text_data=json.dumps(
                {"notification": notification_data, "unread_count": unread_count}
            )
        )


class TaskConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time task updates
    """

    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection
        """
        self.user = self.scope["user"]

        # Accept connection first
        await self.accept()

        # If not authenticated, send a message indicating they need to authenticate
        if not self.user.is_authenticated:
            print(
                f"User not authenticated for task connection, sending auth required message"
            )
            await self.send(
                text_data=json.dumps(
                    {"error": "Authentication required", "authenticated": False}
                )
            )
            return

        # Add this channel to task updates group
        self.task_group_name = "task_updates"
        await self.channel_layer.group_add(self.task_group_name, self.channel_name)

    async def disconnect(self, close_code):
        """
        Called when the WebSocket closes for any reason
        """
        # Remove this channel from the task group
        if hasattr(self, "task_group_name"):
            await self.channel_layer.group_discard(
                self.task_group_name, self.channel_name
            )

    async def receive(self, text_data):
        """
        Called when we get a message from the client
        """
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get("action")

            if action == "update_task":
                task_id = text_data_json.get("task_id")
                status = text_data_json.get("status")
                # Update task and notify all connected clients
                await self.update_task(task_id, status)
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))

    @database_sync_to_async
    def update_task(self, task_id, status):
        """
        Update a task's status
        """
        from apps.tasks.models import Task

        task = Task.objects.get(id=task_id)

        # Check if user has permission to update this task
        if (
            self.user.is_admin()
            or task.created_by == self.user
            or task.assigned_to == self.user
        ):
            task.status = status
            task.save()

            # Send task update to all clients
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "task_updates",
                {
                    "type": "task_update",
                    "task": {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "updated_by": self.user.username,
                    },
                },
            )

    async def task_update(self, event):
        """
        Handler for task.update type events
        """
        # Send a task update to the WebSocket
        await self.send(
            text_data=json.dumps({"task_update": True, "task": event["task"]})
        )
