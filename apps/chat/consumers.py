import json
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import base64
import uuid

class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat messaging with enhanced features
    """
    
    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection
        """
        self.user = self.scope["user"]
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        # Accept connection first
        await self.accept()
        
        # If not authenticated, send a message indicating they need to authenticate
        if not self.user.is_authenticated:
            print(f"User not authenticated for chat room, sending auth required message")
            await self.send(text_data=json.dumps({
                'error': 'Authentication required',
                'authenticated': False
            }))
            return
        
        # Check if user is a member of this chat room
        if not await self.is_room_member():
            await self.send(text_data=json.dumps({
                'error': 'You are not a member of this chat room',
                'access_denied': True
            }))
            await self.close()
            return
        
        # Add this channel to the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Inform the room that a new user has joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_system_message',
                'message': f'{self.user.username} has joined the chat'
            }
        )
        
        # Update online status
        await self.update_user_presence(True)
    
    async def disconnect(self, code):
        """
        Called when the WebSocket closes for any reason
        """
        if hasattr(self, 'room_group_name'):
            # Inform the room that a user has left
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_system_message',
                    'message': f'{self.user.username} has left the chat'
                }
            )
            
            # Remove this channel from the room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            # Update online status
            await self.update_user_presence(False)
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Called when we get a message from the client
        """
        try:
            # Exit early if no text data
            if not text_data:
                return
                
            # Parse the JSON data
            data = json.loads(text_data)
            print(f"Received WebSocket data: {data}")
            
            # Handle regular text messages
            if 'message' in data:
                message = data.get('message', '').strip()
                
                if message:
                    # Print debug info
                    print(f"Received message from {self.user.username}: {message[:50]}")
                    
                    # Check for image messages
                    image_data = None
                    if message.startswith('[Image:') and '\n' in message:
                        try:
                            # Extract image data
                            image_name = message.split('[Image:')[1].split(']')[0].strip()
                            base64_data = message.split('\n')[1]
                            
                            # Process and store image
                            if base64_data.startswith('data:image/'):
                                image_data = await self.save_image(base64_data, image_name)
                                message = f"[Image: {image_data['filename']}]({image_data['url']})"
                        except Exception as e:
                            print(f"Error processing image: {str(e)}")
                    
                    # Save the message to the database
                    chat_message = await self.save_message(message)
                    
                    # Format the sender's full name
                    full_name = self.user.get_full_name() or self.user.username
                    
                    # Create message data
                    message_data = {
                        'type': 'chat_message',
                        'message': message,
                        'message_id': chat_message.id,
                        'user_id': self.user.id,
                        'username': full_name,
                        'timestamp': chat_message.created_at.isoformat()
                    }
                    
                    if image_data:
                        message_data['image_data'] = image_data
                        
                    # Send message to room group
                    print(f"Sending message to group {self.room_group_name}")
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        message_data
                    )
            
            # Handle typing indicator
            elif 'typing' in data:
                is_typing = data.get('typing', False)
                
                # Send typing status to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'user_id': self.user.id,
                        'username': self.user.get_full_name() or self.user.username,
                        'is_typing': is_typing
                    }
                )
            
            # Handle message reactions
            elif 'reaction' in data:
                reaction = data.get('reaction')
                message_id = data.get('message_id')
                
                if reaction and message_id:
                    # Save reaction to database
                    success = await self.toggle_reaction(message_id, reaction)
                    
                    if success:
                        # Send reaction to room group
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'message_reaction',
                                'message_id': message_id,
                                'user_id': self.user.id,
                                'username': self.user.get_full_name() or self.user.username,
                                'reaction': reaction
                            }
                        )
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def chat_message(self, event):
        """
        Handler for chat.message type events
        """
        # Send the message to the WebSocket
        message_data = {
            'type': 'message',
            'message': event['message'],
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp']
        }
        
        # Add image data if present
        if 'image_data' in event and event['image_data']:
            message_data['image_data'] = event['image_data']
        
        await self.send(text_data=json.dumps(message_data))
    
    async def chat_system_message(self, event):
        """
        Handler for system messages (join/leave)
        """
        # Send the system message to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': event['message'],
            'timestamp': timezone.now().isoformat()
        }))
    
    async def typing_indicator(self, event):
        """
        Handler for typing indicator events
        """
        # Send the typing indicator to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))
    
    async def message_reaction(self, event):
        """
        Handler for message reaction events
        """
        # Send the reaction to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'username': event['username'],
            'reaction': event['reaction']
        }))
    
    @database_sync_to_async
    def is_room_member(self):
        """
        Check if the current user is a member of the chat room
        """
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return room.members.filter(id=self.user.id).exists()
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def update_user_presence(self, is_online):
        """
        Update user presence status in the chat room
        """
        # In a full implementation, this would update a UserPresence model
        # For now, just broadcast the status change
        pass
    
    @database_sync_to_async
    def save_image(self, base64_data, image_name):
        """
        Save an image from base64 data
        """
        # Extract the actual base64 string and file type
        format, imgstr = base64_data.split(';base64,')
        ext = format.split('/')[-1]
        
        # Generate a unique filename
        filename = f"{uuid.uuid4()}.{ext}"
        data = ContentFile(base64.b64decode(imgstr))
        
        # Save the file
        path = default_storage.save(f"chat_images/{filename}", data)
        
        # Return the URL and metadata
        return {
            'url': default_storage.url(path),
            'filename': image_name,
            'mime_type': format.split(':')[1]
        }
    
    @database_sync_to_async
    def save_message(self, message):
        """
        Save a new message to the database and create notifications
        """
        from .models import ChatRoom, ChatMessage
        from apps.notifications.models import Notification
        from django.urls import reverse
        
        room = ChatRoom.objects.get(id=self.room_id)
        chat_message = ChatMessage.objects.create(
            room=room,
            sender=self.user,
            content=message
        )
        
        # Create notifications for all other members
        sender_name = self.user.get_full_name() or self.user.username
        room_members = room.members.exclude(id=self.user.id)
        
        # Debug info - who are the room members
        print(f"Room {room.id} has {room_members.count()} members besides sender")
        for debug_member in room_members:
            print(f"  - Member: {debug_member.id} - {debug_member.username}")
        
        for member in room_members:
            # Create notification for new message - format like the sample screenshot
            notification = Notification.objects.create(
                user=member,
                title=f"New message in {room.name}",
                message=f"{sender_name}: {self.format_notification_text(message)}",
                link=reverse('chat:detail', kwargs={'pk': room.id}),
                notification_type='chat_message'
            )
            
            # Send notification directly through the channel layer
            # For WebSocket notifications
            try:
                # Get channel layer
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                
                # Prepare notification data - make sure type matches the handler in NotificationConsumer
                notification_data = {
                    'type': 'notification_message',  # This must match the method name in NotificationConsumer
                    'notification': {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'link': notification.link,
                        'is_read': notification.is_read,
                        'created_at': notification.created_at.isoformat(),
                        'notification_type': notification.notification_type
                    },
                    'unread_count': self.get_user_unread_count(member)
                }
                
                # User-specific notification group
                user_group_name = f'notifications_{member.id}'
                
                # Print debug info for notification
                print(f"Sending notification to {user_group_name}: {notification_data}")
                
                # In the sync context, we need to use async_to_sync 
                # rather than trying to use asyncio.create_task
                from asgiref.sync import async_to_sync
                async_to_sync(channel_layer.group_send)(
                    user_group_name, 
                    notification_data
                )
                
            except Exception as e:
                print(f"Error sending notification: {str(e)}")
        
        return chat_message
    
    @database_sync_to_async
    def toggle_reaction(self, message_id, reaction):
        """
        Toggle a reaction on a message
        """
        # In a full implementation, this would save to a MessageReaction model
        # For now, just return success
        return True
    
    def format_notification_text(self, message):
        """
        Format message text for notifications, handling special messages
        """
        # Handle image messages
        if message.startswith('[Image:'):
            return "📷 Sent an image"
        
        # Truncate long messages
        if len(message) > 50:
            return message[:50] + '...'
            
        return message
        
    def get_user_unread_count(self, user):
        """
        Get count of unread notifications for a user
        """
        from apps.notifications.models import Notification
        return Notification.objects.filter(user=user, is_read=False).count()