from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Notification

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 10
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Notifications'
        return context

@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    
    # If notification has a link, redirect to it
    if notification.link:
        return redirect(notification.link)
    
    return redirect('notifications:list')

@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications:list')

class NotificationDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Notification
    success_url = reverse_lazy('notifications:list')
    
    def test_func(self):
        notification = self.get_object()
        return self.request.user == notification.user
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Notification deleted.')
        return super().delete(request, *args, **kwargs)

@login_required
def get_unread_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})

@login_required
def get_recent_notifications(request):
    """
    Get the 5 most recent notifications for the current user
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    notifications_data = [{
        'id': notification.id,
        'title': notification.title,
        'message': notification.message,
        'link': notification.link,
        'is_read': notification.is_read,
        'created_at': notification.created_at.isoformat(),
        'notification_type': notification.notification_type
    } for notification in notifications]
    
    return JsonResponse({
        'notifications': notifications_data,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count()
    })
