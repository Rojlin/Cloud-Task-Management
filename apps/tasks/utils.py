from django.contrib.auth.models import User
from django.shortcuts import render

from apps.accounts.models import UserProfile
from apps.notifications.models import Notification


def handle_permission_denied(request, action=None):
    """
    Handle permission denied cases by showing custom page and notifying admins
    """
    # Send notification to all admins
    admin_users = User.objects.filter(userprofile__role=UserProfile.ADMIN)

    for admin in admin_users:
        Notification.objects.create(
            user=admin,
            title="Unauthorized Access Attempt",
            message=f"User {request.user.username} ({request.user.userprofile.get_role_display()}) attempted to {action or 'access restricted resource'} but was denied due to insufficient privileges.",
            type="warning",
        )

    # Render custom permission denied page
    context = {"action": action, "user": request.user}
    return render(request, "errors/permission_denied.html", context, status=403)


def send_overdue_notifications():
    """
    Send notifications for overdue tasks
    """
    from datetime import timedelta

    from django.utils import timezone

    from .models import Task

    # Get tasks that are overdue
    overdue_tasks = Task.objects.filter(
        due_date__lt=timezone.now().date(),
        status__in=[Task.TODO, Task.IN_PROGRESS, Task.REVIEW],
    ).select_related("assigned_to", "project", "created_by")

    for task in overdue_tasks:
        # Check if we already sent an overdue notification for this task
        existing_notification = Notification.objects.filter(
            user=task.assigned_to,
            title__contains="Overdue Task",
            message__contains=task.title,
            created_at__date=timezone.now().date(),
        ).exists()

        if not existing_notification and task.assigned_to:
            days_overdue = (timezone.now().date() - task.due_date).days

            Notification.objects.create(
                user=task.assigned_to,
                title="Overdue Task Alert",
                message=f"Task '{task.title}' in project '{task.project.name}' is {days_overdue} days overdue. Please update the status or contact your project manager.",
                type="danger",
            )

            # Also notify project manager if different from assigned user
            if task.project.created_by != task.assigned_to:
                Notification.objects.create(
                    user=task.project.created_by,
                    title="Team Member Has Overdue Task",
                    message=f"{task.assigned_to.get_full_name() or task.assigned_to.username} has an overdue task: '{task.title}' ({days_overdue} days overdue)",
                    type="warning",
                )
