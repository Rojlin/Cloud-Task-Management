from django.core.management.base import BaseCommand
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from apps.tasks.models import Task
from apps.notifications.models import Notification

class Command(BaseCommand):
    help = 'Checks for tasks with approaching deadlines and sends notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Days threshold for approaching deadlines'
        )

    def handle(self, *args, **options):
        days_threshold = options['days']
        today = timezone.now().date()
        deadline_date = today + timedelta(days=days_threshold)
        
        # Find tasks that are approaching their deadline
        approaching_tasks = Task.objects.filter(
            status__in=[Task.TODO, Task.IN_PROGRESS, Task.REVIEW],  # Not completed
            due_date__lte=deadline_date,
            due_date__gt=today  # Not overdue yet
        )
        
        self.stdout.write(f"Found {approaching_tasks.count()} tasks with approaching deadlines")
        
        for task in approaching_tasks:
            days_left = (task.due_date - today).days
            
            # Send notification to assigned user if task is assigned
            if task.assigned_to:
                # Check if a notification for this task's deadline was sent recently
                recent_notification = Notification.objects.filter(
                    user=task.assigned_to,
                    title='Approaching Task Deadline',
                    link=reverse('tasks:detail', kwargs={'pk': task.id}),
                    created_at__gte=timezone.now() - timedelta(days=1)  # Don't send more than once a day
                ).exists()
                
                if not recent_notification:
                    Notification.objects.create(
                        user=task.assigned_to,
                        title='Approaching Task Deadline',
                        message=f'Task "{task.title}" is due in {days_left} day{"s" if days_left != 1 else ""}.',
                        link=reverse('tasks:detail', kwargs={'pk': task.id})
                    )
                    self.stdout.write(f"Sent deadline notification for task {task.id} to {task.assigned_to.username}")
            
            # Send notification to task creator if different from assigned user
            if task.created_by and task.created_by != task.assigned_to:
                # Check if a notification for this task's deadline was sent recently
                recent_notification = Notification.objects.filter(
                    user=task.created_by,
                    title='Approaching Task Deadline',
                    link=reverse('tasks:detail', kwargs={'pk': task.id}),
                    created_at__gte=timezone.now() - timedelta(days=1)  # Don't send more than once a day
                ).exists()
                
                if not recent_notification:
                    Notification.objects.create(
                        user=task.created_by,
                        title='Approaching Task Deadline',
                        message=f'Task "{task.title}" is due in {days_left} day{"s" if days_left != 1 else ""}.',
                        link=reverse('tasks:detail', kwargs={'pk': task.id})
                    )
                    self.stdout.write(f"Sent deadline notification for task {task.id} to {task.created_by.username}")
        
        self.stdout.write(self.style.SUCCESS('Successfully checked for approaching deadlines'))
