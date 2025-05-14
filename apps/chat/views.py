from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json

from .models import ChatRoom, ChatMessage

User = get_user_model()

class ChatRoomListView(LoginRequiredMixin, ListView):
    model = ChatRoom
    template_name = 'chat/index.html'
    context_object_name = 'chat_rooms'
    
    def get_queryset(self):
        return ChatRoom.objects.filter(members=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Chat Rooms'
        return context

class ChatRoomDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = ChatRoom
    template_name = 'chat/detail.html'
    context_object_name = 'chat_room'
    
    def test_func(self):
        room = self.get_object()
        return self.request.user in room.members.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room = self.get_object()
        context['messages'] = room.messages.all()
        context['title'] = f'Chat: {room.name}'
        return context

class ChatRoomCreateView(LoginRequiredMixin, CreateView):
    model = ChatRoom
    template_name = 'chat/create.html'
    fields = ['name', 'description']
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Add creator as a member
        self.object.members.add(self.request.user)
        
        messages.success(self.request, f'Chat room "{self.object.name}" created successfully.')
        return response
    
    def get_success_url(self):
        return reverse('chat:add_members', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Chat Room'
        context['action'] = 'Create'
        return context

class ChatRoomUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ChatRoom
    template_name = 'chat/edit.html'
    fields = ['name', 'description']
    
    def test_func(self):
        room = self.get_object()
        return self.request.user == room.created_by or self.request.user.is_admin
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Chat room "{self.object.name}" updated successfully.')
        return response
    
    def get_success_url(self):
        return reverse('chat:detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Chat Room: {self.object.name}'
        context['action'] = 'Update'
        return context

class ChatRoomDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ChatRoom
    template_name = 'chat/delete.html'
    success_url = reverse_lazy('chat:list')
    
    def test_func(self):
        room = self.get_object()
        return self.request.user == room.created_by or self.request.user.is_admin
    
    def delete(self, request, *args, **kwargs):
        room = self.get_object()
        messages.success(self.request, f'Chat room "{room.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Delete Chat Room: {self.object.name}'
        return context

class ChatRoomAddMembersView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = ChatRoom
    template_name = 'chat/add_members.html'
    context_object_name = 'chat_room'
    
    def test_func(self):
        room = self.get_object()
        return self.request.user == room.created_by or self.request.user.is_admin
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room = self.get_object()
        
        # Get users not in the room
        context['available_users'] = User.objects.exclude(
            id__in=room.members.values_list('id', flat=True)
        )
        
        context['title'] = f'Add Members to {room.name}'
        return context
    
    def post(self, request, *args, **kwargs):
        room = self.get_object()
        user_ids = request.POST.getlist('members')  # Changed from 'users' to match the form
        
        added_users = []
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                room.members.add(user)
                added_users.append(user)
                
                # Create notification for the added user
                from apps.notifications.models import Notification
                Notification.objects.create(
                    user=user,
                    title="Added to Chat Room",
                    message=f"You were added to the chat room: {room.name} by {request.user.get_full_name() or request.user.username}",
                    link=reverse('chat:detail', kwargs={'pk': room.pk})
                )
                
            except User.DoesNotExist:
                continue
        
        # If users were added, send a system message to the chat
        if added_users:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            # Get the channel layer
            channel_layer = get_channel_layer()
            room_group_name = f'chat_{room.id}'
            
            # Create a comma-separated list of added users
            usernames = ", ".join([user.get_full_name() or user.username for user in added_users])
            
            # Send system message
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'chat_system_message',
                    'message': f"{usernames} has been added to the chat by {request.user.get_full_name() or request.user.username}"
                }
            )
        
        messages.success(request, f'Members added to chat room "{room.name}" successfully.')
        return redirect('chat:detail', pk=room.pk)

@login_required
def get_messages(request, room_id):
    room = get_object_or_404(ChatRoom, pk=room_id)
    
    # Check if user is a member of the room
    if request.user not in room.members.all():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get messages, possibly with pagination
    messages = room.messages.all().order_by('-created_at')[:50]  # Get last 50 messages
    
    # Format for JSON response
    messages_data = []
    for msg in reversed(messages):
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'sender': msg.sender.username,
            'sender_id': msg.sender.id,
            'is_own': msg.sender.id == request.user.id,
            'timestamp': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return JsonResponse({'messages': messages_data})

@csrf_exempt
@login_required
def send_message(request, room_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    room = get_object_or_404(ChatRoom, pk=room_id)
    
    # Check if user is a member of the room
    if request.user not in room.members.all():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'error': 'Message content cannot be empty'}, status=400)
        
        # Create the message
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            content=content
        )
        
        # Return message data
        return JsonResponse({
            'id': message.id,
            'content': message.content,
            'sender': message.sender.username,
            'sender_id': message.sender.id,
            'is_own': True,
            'timestamp': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
