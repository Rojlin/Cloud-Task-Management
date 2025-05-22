import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember

from .forms import TaskAttachmentForm, TaskCommentForm, TaskFilterForm, TaskForm
from .models import Task, TaskAttachment, TaskComment
from .utils import handle_permission_denied


class TaskAccessMixin(UserPassesTestMixin):
    """
    Mixin to check if user has access to a task
    """

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False

        # Check if admin first
        if self.request.user.is_admin:
            return True

        # Get task from kwargs
        task_id = self.kwargs.get("pk") or self.kwargs.get("task_id")
        if not task_id:
            return True  # No task to check against (for list views)

        task = get_object_or_404(Task, pk=task_id)

        # Check if user is task creator
        if task.created_by == self.request.user:
            return True

        # Check if user is task assignee
        if task.assigned_to == self.request.user:
            return True

        # Check if user is a member of the task's project
        return ProjectMember.objects.filter(
            project=task.project, user=self.request.user
        ).exists()


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/list.html"
    context_object_name = "tasks"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter based on user role
        if not user.is_admin:
            queryset = queryset.filter(
                Q(project__created_by=user)
                | Q(project__members=user)
                | Q(created_by=user)
                | Q(assigned_to=user)
            ).distinct()

        # Apply filters
        form = TaskFilterForm(self.request.GET, user=user)
        if form.is_valid():
            title = form.cleaned_data.get("title")
            status = form.cleaned_data.get("status")
            priority = form.cleaned_data.get("priority")
            assigned_to = form.cleaned_data.get("assigned_to")
            due_date_from = form.cleaned_data.get("due_date_from")
            due_date_to = form.cleaned_data.get("due_date_to")

            if title:
                queryset = queryset.filter(title__icontains=title)
            if status:
                queryset = queryset.filter(status=status)
            if priority:
                queryset = queryset.filter(priority=priority)
            if assigned_to:
                queryset = queryset.filter(assigned_to=assigned_to)
            if due_date_from:
                queryset = queryset.filter(due_date__gte=due_date_from)
            if due_date_to:
                queryset = queryset.filter(due_date__lte=due_date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = TaskFilterForm(
            self.request.GET, user=self.request.user
        )
        context["title"] = "All Tasks"

        # Add counts for dashboard
        user = self.request.user
        if user.is_admin:
            tasks = Task.objects.all()
        else:
            tasks = Task.objects.filter(
                Q(project__created_by=user)
                | Q(project__members=user)
                | Q(created_by=user)
                | Q(assigned_to=user)
            ).distinct()

        context["total_tasks"] = tasks.count()
        context["completed_tasks"] = tasks.filter(status=Task.COMPLETED).count()
        context["overdue_tasks"] = (
            tasks.filter(due_date__lt=timezone.now().date())
            .exclude(status=Task.COMPLETED)
            .count()
        )
        context["my_tasks"] = tasks.filter(assigned_to=user).count()

        return context


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user

        # If creating from a specific project
        project_id = self.request.GET.get("project")
        if project_id:
            kwargs["project_id"] = project_id

        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        # Create notification for the assignee if there is one
        if form.instance.assigned_to and form.instance.assigned_to != self.request.user:
            notification = Notification.objects.create(
                user=form.instance.assigned_to,
                title="New Task Assigned",
                message=f'You have been assigned to task "{form.instance.title}" in project "{form.instance.project.name}"',
                link=reverse("tasks:detail", kwargs={"pk": form.instance.id}),
                notification_type="task_assigned",
            )

            # Send real-time notification
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()

            notification_group_name = f"notifications_{form.instance.assigned_to.id}"
            async_to_sync(channel_layer.group_send)(
                notification_group_name,
                {
                    "type": "notification_message",
                    "message": {
                        "title": "New Task Assigned",
                        "content": f'You have been assigned to task "{form.instance.title}" in project "{form.instance.project.name}"',
                        "link": reverse(
                            "tasks:detail", kwargs={"pk": form.instance.id}
                        ),
                    },
                },
            )

        # Notify project manager and project members about the new task
        project = form.instance.project
        project_members = project.members.exclude(id=self.request.user.id)

        # Get the project manager of this project
        project_manager = ProjectMember.objects.filter(
            project=project, role=ProjectMember.PROJECT_MANAGER
        ).first()

        # We need to import these for real-time notifications
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()

        if project_manager and project_manager.user.id != self.request.user.id:
            # Create notification for project manager
            notification = Notification.objects.create(
                user=project_manager.user,
                title="New Task Created",
                message=f'{self.request.user.username} created a new task "{form.instance.title}" in project "{project.name}"',
                link=reverse("tasks:detail", kwargs={"pk": form.instance.id}),
                notification_type="task_created",
            )

            # Send real-time notification to project manager
            notification_group_name = f"notifications_{project_manager.user.id}"
            async_to_sync(channel_layer.group_send)(
                notification_group_name,
                {
                    "type": "notification_message",
                    "message": {
                        "title": "New Task Created",
                        "content": f'{self.request.user.username} created a new task "{form.instance.title}" in project "{project.name}"',
                        "link": reverse(
                            "tasks:detail", kwargs={"pk": form.instance.id}
                        ),
                    },
                },
            )

        messages.success(
            self.request, f'Task "{form.instance.title}" created successfully.'
        )

        # Redirect to the task detail page
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Task"
        context["action"] = "Create"

        # If creating from a specific project
        project_id = self.request.GET.get("project")
        if project_id:
            project = get_object_or_404(Project, pk=project_id)
            context["project"] = project

        return context


class TaskDetailView(LoginRequiredMixin, TaskAccessMixin, DetailView):
    model = Task
    template_name = "tasks/detail.html"
    context_object_name = "task"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.get_object()

        context["comment_form"] = TaskCommentForm()
        context["attachment_form"] = TaskAttachmentForm()
        context["comments"] = task.comments.all()
        context["attachments"] = task.attachments.all()
        context["title"] = f"Task: {task.title}"

        # Check if user has edit permissions
        user = self.request.user
        can_edit = user.is_admin or task.created_by == user

        # Project managers and leaders can also edit tasks
        if not can_edit:
            project_member = ProjectMember.objects.filter(
                project=task.project, user=user
            ).first()
            if project_member and project_member.role in [
                ProjectMember.PROJECT_MANAGER,
                ProjectMember.LEADER,
            ]:
                can_edit = True

        context["can_edit"] = can_edit

        # Team members can update status and add comments/attachments
        context["can_update_status"] = can_edit or task.assigned_to == user

        return context


class TaskUpdateView(LoginRequiredMixin, TaskAccessMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/edit.html"

    def test_func(self):
        if not super().test_func():
            return False

        # Only admin, task creator, project managers, and leaders can edit tasks
        user = self.request.user
        task = self.get_object()

        if user.is_admin or task.created_by == user:
            return True

        # Check if user is a project manager or leader for this project
        project_member = ProjectMember.objects.filter(
            project=task.project, user=user
        ).first()
        return project_member and project_member.role in [
            ProjectMember.PROJECT_MANAGER,
            ProjectMember.LEADER,
        ]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        old_task = self.get_object()
        response = super().form_valid(form)

        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()

        # List of changes for notifications
        changes = []

        # Check if assigned user changed
        if (
            form.instance.assigned_to
            and old_task.assigned_to != form.instance.assigned_to
        ):
            # Create notification in database
            notification = Notification.objects.create(
                user=form.instance.assigned_to,
                title="Task Assigned",
                message=f'You have been assigned to task "{form.instance.title}" in project "{form.instance.project.name}"',
                link=reverse("tasks:detail", kwargs={"pk": form.instance.id}),
                notification_type="task_assigned",
            )

            # Add to changes list
            changes.append("assignee")

            # Send real-time notification
            notification_group_name = f"notifications_{form.instance.assigned_to.id}"
            async_to_sync(channel_layer.group_send)(
                notification_group_name,
                {
                    "type": "notification_message",
                    "message": {
                        "title": "Task Assigned",
                        "content": f'You have been assigned to task "{form.instance.title}" in project "{form.instance.project.name}"',
                        "link": reverse(
                            "tasks:detail", kwargs={"pk": form.instance.id}
                        ),
                    },
                },
            )

        # Check if status changed
        if old_task.status != form.instance.status:
            changes.append("status")

            # Notify task creator and project manager about status change
            users_to_notify = []
            if old_task.created_by != self.request.user:
                users_to_notify.append(old_task.created_by)

            # Get project manager
            project_manager = ProjectMember.objects.filter(
                project=form.instance.project, role=ProjectMember.PROJECT_MANAGER
            ).first()

            if project_manager and project_manager.user != self.request.user:
                users_to_notify.append(project_manager.user)

            # Create notifications and send real-time updates
            for user in users_to_notify:
                notification = Notification.objects.create(
                    user=user,
                    title="Task Status Updated",
                    message=f'Task "{form.instance.title}" status updated to {form.instance.get_status_display()} by {self.request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": form.instance.id}),
                    notification_type="task_status_updated",
                )

                # Send real-time notification
                notification_group_name = f"notifications_{user.id}"
                async_to_sync(channel_layer.group_send)(
                    notification_group_name,
                    {
                        "type": "notification_message",
                        "message": {
                            "title": "Task Status Updated",
                            "content": f'Task "{form.instance.title}" status updated to {form.instance.get_status_display()} by {self.request.user.username}',
                            "link": reverse(
                                "tasks:detail", kwargs={"pk": form.instance.id}
                            ),
                        },
                    },
                )

        # Check if priority changed
        if old_task.priority != form.instance.priority:
            changes.append("priority")

            # Similar notifications for priority changes
            if old_task.assigned_to and old_task.assigned_to != self.request.user:
                notification = Notification.objects.create(
                    user=old_task.assigned_to,
                    title="Task Priority Updated",
                    message=f'Task "{form.instance.title}" priority updated to {form.instance.get_priority_display()} by {self.request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": form.instance.id}),
                    notification_type="task_priority_updated",
                )

                # Send real-time notification
                notification_group_name = f"notifications_{old_task.assigned_to.id}"
                async_to_sync(channel_layer.group_send)(
                    notification_group_name,
                    {
                        "type": "notification_message",
                        "message": {
                            "title": "Task Priority Updated",
                            "content": f'Task "{form.instance.title}" priority updated to {form.instance.get_priority_display()} by {self.request.user.username}',
                            "link": reverse(
                                "tasks:detail", kwargs={"pk": form.instance.id}
                            ),
                        },
                    },
                )

        # Check if due date changed
        if old_task.due_date != form.instance.due_date:
            changes.append("due date")

            if (
                form.instance.assigned_to
                and form.instance.assigned_to != self.request.user
            ):
                notification = Notification.objects.create(
                    user=form.instance.assigned_to,
                    title="Task Due Date Updated",
                    message=f'Task "{form.instance.title}" due date updated to {form.instance.due_date} by {self.request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": form.instance.id}),
                    notification_type="task_due_date_updated",
                )

                # Send real-time notification
                notification_group_name = (
                    f"notifications_{form.instance.assigned_to.id}"
                )
                async_to_sync(channel_layer.group_send)(
                    notification_group_name,
                    {
                        "type": "notification_message",
                        "message": {
                            "title": "Task Due Date Updated",
                            "content": f'Task "{form.instance.title}" due date updated to {form.instance.due_date} by {self.request.user.username}',
                            "link": reverse(
                                "tasks:detail", kwargs={"pk": form.instance.id}
                            ),
                        },
                    },
                )

        # Success message with details of what changed
        if changes:
            change_msg = ", ".join(changes)
            messages.success(
                self.request,
                f'Task "{form.instance.title}" updated successfully. Changed: {change_msg}.',
            )
        else:
            messages.success(
                self.request, f'Task "{form.instance.title}" updated successfully.'
            )

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Task: {self.object.title}"
        context["action"] = "Update"
        return context


class TaskDeleteView(LoginRequiredMixin, TaskAccessMixin, DeleteView):
    model = Task
    template_name = "tasks/delete.html"
    success_url = reverse_lazy("tasks:list")
    context_object_name = "task"

    def test_func(self):
        if not super().test_func():
            return False

        # Only admin, task creator, project managers can delete tasks
        user = self.request.user
        task = self.get_object()

        if user.is_admin or task.created_by == user:
            return True

        # Check if user is a project manager for this project
        project_member = ProjectMember.objects.filter(
            project=task.project, user=user
        ).first()
        return project_member and project_member.role == ProjectMember.PROJECT_MANAGER

    def handle_no_permission(self):
        # Use our custom permission denied handler
        return handle_permission_denied(self.request, "delete this task")

    def delete(self, request, *args, **kwargs):
        task = self.get_object()
        messages.success(self.request, f'Task "{task.title}" deleted successfully.')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Delete Task: {self.object.title}"
        return context


class TaskStatusUpdateView(LoginRequiredMixin, TaskAccessMixin, View):
    def get(self, request, *args, **kwargs):
        task = get_object_or_404(Task, pk=self.kwargs["pk"])
        status = self.kwargs["status"]

        # Validate status
        if status not in dict(Task.STATUS_CHOICES).keys():
            messages.error(request, "Invalid status.")
            return redirect("tasks:detail", pk=task.pk)

        # Update the task status
        task.status = status
        task.save()

        # Create notification for task creator and assigned user if not the current user
        for user in [task.created_by, task.assigned_to]:
            if user and user != request.user:
                Notification.objects.create(
                    user=user,
                    title="Task Status Updated",
                    message=f'The status of task "{task.title}" has been updated to {task.get_status_display()} by {request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": task.id}),
                )

        messages.success(
            request, f"Task status updated to {task.get_status_display()}."
        )

        # Redirect back to referer or task detail
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return HttpResponseRedirect(referer)
        return redirect("tasks:detail", pk=task.pk)

    def post(self, request, *args, **kwargs):
        task = get_object_or_404(Task, pk=self.kwargs["pk"])
        status = request.POST.get("status")

        # Validate status
        if status not in dict(Task.STATUS_CHOICES).keys():
            messages.error(request, "Invalid status.")
            return redirect("tasks:detail", pk=task.pk)

        # Update the task status
        task.status = status
        task.save()

        # Create notification for task creator and assigned user if not the current user
        for user in [task.created_by, task.assigned_to]:
            if user and user != request.user:
                Notification.objects.create(
                    user=user,
                    title="Task Status Updated",
                    message=f'The status of task "{task.title}" has been updated to {task.get_status_display()} by {request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": task.id}),
                )

        messages.success(
            request, f"Task status updated to {task.get_status_display()}."
        )

        # Redirect back to referer or task detail
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return HttpResponseRedirect(referer)
        return redirect("tasks:detail", pk=task.pk)


class TaskPriorityUpdateView(LoginRequiredMixin, TaskAccessMixin, View):
    def get(self, request, *args, **kwargs):
        task = get_object_or_404(Task, pk=self.kwargs["pk"])
        priority = self.kwargs["priority"]

        # Validate priority
        if priority not in dict(Task.PRIORITY_CHOICES).keys():
            messages.error(request, "Invalid priority.")
            return redirect("tasks:detail", pk=task.pk)

        # Update the task priority
        task.priority = priority
        task.save()

        # Create notification for task creator and assigned user if not the current user
        for user in [task.created_by, task.assigned_to]:
            if user and user != request.user:
                Notification.objects.create(
                    user=user,
                    title="Task Priority Updated",
                    message=f'The priority of task "{task.title}" has been updated to {task.get_priority_display()} by {request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": task.id}),
                )

        messages.success(
            request, f"Task priority updated to {task.get_priority_display()}."
        )

        # Redirect back to referer or task detail
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return HttpResponseRedirect(referer)
        return redirect("tasks:detail", pk=task.pk)

    def post(self, request, *args, **kwargs):
        task = get_object_or_404(Task, pk=self.kwargs["pk"])
        priority = request.POST.get("priority")

        # Validate priority
        if priority not in dict(Task.PRIORITY_CHOICES).keys():
            messages.error(request, "Invalid priority.")
            return redirect("tasks:detail", pk=task.pk)

        # Update the task priority
        task.priority = priority
        task.save()

        # Create notification for task creator and assigned user if not the current user
        for user in [task.created_by, task.assigned_to]:
            if user and user != request.user:
                Notification.objects.create(
                    user=user,
                    title="Task Priority Updated",
                    message=f'The priority of task "{task.title}" has been updated to {task.get_priority_display()} by {request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": task.id}),
                )

        messages.success(
            request, f"Task priority updated to {task.get_priority_display()}."
        )

        # Redirect back to referer or task detail
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return HttpResponseRedirect(referer)
        return redirect("tasks:detail", pk=task.pk)


class TaskCommentCreateView(LoginRequiredMixin, TaskAccessMixin, CreateView):
    model = TaskComment
    form_class = TaskCommentForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task"] = get_object_or_404(Task, pk=self.kwargs["task_id"])
        return context

    def form_valid(self, form):
        task = get_object_or_404(Task, pk=self.kwargs["task_id"])
        form.instance.task = task
        form.instance.user = self.request.user
        response = super().form_valid(form)

        # Create notification for task creator and assignee if not the current user
        for user in [task.created_by, task.assigned_to]:
            if user and user != self.request.user:
                Notification.objects.create(
                    user=user,
                    title="New Comment on Task",
                    message=f'New comment on task "{task.title}" by {self.request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": task.id}),
                )

        messages.success(self.request, "Comment added successfully.")
        return response

    def get_success_url(self):
        return reverse("tasks:detail", kwargs={"pk": self.kwargs["task_id"]})


class TaskCommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = TaskComment

    def test_func(self):
        comment = self.get_object()
        user = self.request.user

        # User can delete their own comments or if they are admin
        if user.is_admin or comment.user == user:
            return True

        # Project managers and task creators can delete comments
        task = comment.task
        if task.created_by == user:
            return True

        project_member = ProjectMember.objects.filter(
            project=task.project, user=user
        ).first()
        return project_member and project_member.role == ProjectMember.PROJECT_MANAGER

    def get_success_url(self):
        return reverse("tasks:detail", kwargs={"pk": self.object.task.id})

    def delete(self, request, *args, **kwargs):
        comment = self.get_object()
        messages.success(request, "Comment deleted successfully.")
        return super().delete(request, *args, **kwargs)


class TaskAttachmentCreateView(LoginRequiredMixin, TaskAccessMixin, CreateView):
    model = TaskAttachment
    form_class = TaskAttachmentForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task"] = get_object_or_404(Task, pk=self.kwargs["task_id"])
        return context

    def form_valid(self, form):
        task = get_object_or_404(Task, pk=self.kwargs["task_id"])
        form.instance.task = task
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)

        # Create notification for task creator and assignee if not the current user
        for user in [task.created_by, task.assigned_to]:
            if user and user != self.request.user:
                Notification.objects.create(
                    user=user,
                    title="New Attachment on Task",
                    message=f'New attachment added to task "{task.title}" by {self.request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": task.id}),
                )

        messages.success(self.request, "Attachment added successfully.")
        return response

    def get_success_url(self):
        return reverse("tasks:detail", kwargs={"pk": self.kwargs["task_id"]})


class TaskAttachmentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = TaskAttachment

    def test_func(self):
        attachment = self.get_object()
        user = self.request.user

        # User can delete their own attachments or if they are admin
        if user.is_admin or attachment.uploaded_by == user:
            return True

        # Project managers and task creators can delete attachments
        task = attachment.task
        if task.created_by == user:
            return True

        project_member = ProjectMember.objects.filter(
            project=task.project, user=user
        ).first()
        return project_member and project_member.role == ProjectMember.PROJECT_MANAGER

    def get_success_url(self):
        return reverse("tasks:detail", kwargs={"pk": self.object.task.id})

    def delete(self, request, *args, **kwargs):
        attachment = self.get_object()
        messages.success(request, "Attachment deleted successfully.")
        return super().delete(request, *args, **kwargs)


class TaskKanbanView(LoginRequiredMixin, TemplateView):
    template_name = "tasks/kanban.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get tasks based on user role
        if user.is_admin:
            todo_tasks = Task.objects.filter(status=Task.TODO)
            in_progress_tasks = Task.objects.filter(status=Task.IN_PROGRESS)
            review_tasks = Task.objects.filter(status=Task.REVIEW)
            completed_tasks = Task.objects.filter(status=Task.COMPLETED)
        else:
            # Get projects the user is a member of
            user_projects = Project.objects.filter(
                Q(created_by=user) | Q(members=user)
            ).distinct()

            # Get tasks from those projects
            todo_tasks = Task.objects.filter(
                Q(project__in=user_projects) | Q(assigned_to=user), status=Task.TODO
            ).distinct()

            in_progress_tasks = Task.objects.filter(
                Q(project__in=user_projects) | Q(assigned_to=user),
                status=Task.IN_PROGRESS,
            ).distinct()

            review_tasks = Task.objects.filter(
                Q(project__in=user_projects) | Q(assigned_to=user), status=Task.REVIEW
            ).distinct()

            completed_tasks = Task.objects.filter(
                Q(project__in=user_projects) | Q(assigned_to=user),
                status=Task.COMPLETED,
            ).distinct()

        context.update(
            {
                "todo_tasks": todo_tasks,
                "in_progress_tasks": in_progress_tasks,
                "review_tasks": review_tasks,
                "completed_tasks": completed_tasks,
                "title": "Task Kanban Board",
            }
        )

        return context


class ProjectTaskKanbanView(LoginRequiredMixin, TaskAccessMixin, TemplateView):
    template_name = "tasks/kanban.html"

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False

        # Check if admin first
        if self.request.user.is_admin:
            return True

        # Get project from kwargs
        project_id = self.kwargs.get("project_id")
        if not project_id:
            return False

        project = get_object_or_404(Project, pk=project_id)

        # Check if user is project creator
        if project.created_by == self.request.user:
            return True

        # Check if user is a project member
        return ProjectMember.objects.filter(
            project=project, user=self.request.user
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])

        context.update(
            {
                "project": project,
                "todo_tasks": Task.objects.filter(project=project, status=Task.TODO),
                "in_progress_tasks": Task.objects.filter(
                    project=project, status=Task.IN_PROGRESS
                ),
                "review_tasks": Task.objects.filter(
                    project=project, status=Task.REVIEW
                ),
                "completed_tasks": Task.objects.filter(
                    project=project, status=Task.COMPLETED
                ),
                "title": f"Kanban Board: {project.name}",
            }
        )

        return context


class TaskCalendarView(LoginRequiredMixin, TemplateView):
    template_name = "tasks/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # All tasks will be loaded via AJAX
        context["title"] = "Task Calendar"
        return context


class ProjectTaskCalendarView(LoginRequiredMixin, TaskAccessMixin, TemplateView):
    template_name = "tasks/calendar.html"

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False

        # Check if admin first
        if self.request.user.is_admin:
            return True

        # Get project from kwargs
        project_id = self.kwargs.get("project_id")
        if not project_id:
            return False

        project = get_object_or_404(Project, pk=project_id)

        # Check if user is project creator
        if project.created_by == self.request.user:
            return True

        # Check if user is a project member
        return ProjectMember.objects.filter(
            project=project, user=self.request.user
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])

        context.update({"project": project, "title": f"Calendar: {project.name}"})

        return context


@csrf_exempt
@require_POST
@login_required
def update_task_status(request):
    try:
        data = json.loads(request.body)
        task_id = data.get("taskId")
        new_status = data.get("newStatus")

        task = get_object_or_404(Task, pk=task_id)

        # Check if user has permission to update this task
        if (
            not request.user.is_admin
            and request.user != task.created_by
            and request.user != task.assigned_to
            and not ProjectMember.objects.filter(
                project=task.project,
                user=request.user,
                role__in=[ProjectMember.PROJECT_MANAGER, ProjectMember.LEADER],
            ).exists()
        ):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        # Validate the new status
        if new_status not in dict(Task.STATUS_CHOICES).keys():
            return JsonResponse(
                {"status": "error", "message": "Invalid status"}, status=400
            )

        # Update the task
        task.status = new_status
        task.save()

        # Create notification for task creator and assignee if not the current user
        for user in [task.created_by, task.assigned_to]:
            if user and user != request.user:
                Notification.objects.create(
                    user=user,
                    title="Task Status Updated",
                    message=f'The status of task "{task.title}" has been updated to {task.get_status_display()} by {request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": task.id}),
                )

        return JsonResponse(
            {
                "status": "success",
                "message": "Task status updated",
                "newStatus": task.get_status_display(),
                "taskId": task.id,
            }
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def update_task_status_api(request, task_id, status):
    """
    API endpoint for updating task status via AJAX (used as fallback when WebSocket isn't available)
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Method not allowed"}, status=405
        )

    try:
        task = get_object_or_404(Task, pk=task_id)

        # Check if user has permission to update this task
        if (
            not request.user.is_admin
            and request.user != task.created_by
            and request.user != task.assigned_to
            and not ProjectMember.objects.filter(
                project=task.project,
                user=request.user,
                role__in=[ProjectMember.PROJECT_MANAGER, ProjectMember.LEADER],
            ).exists()
        ):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        # Validate the new status
        if status not in dict(Task.STATUS_CHOICES).keys():
            return JsonResponse(
                {"success": False, "error": "Invalid status"}, status=400
            )

        # Update the task
        task.status = status
        task.save()

        # Create notification for task creator and assignee if not the current user
        for user in [task.created_by, task.assigned_to]:
            if user and user != request.user:
                Notification.objects.create(
                    user=user,
                    title="Task Status Updated",
                    message=f'The status of task "{task.title}" has been updated to {task.get_status_display()} by {request.user.username}',
                    link=reverse("tasks:detail", kwargs={"pk": task.id}),
                )

        return JsonResponse(
            {"success": True, "newStatus": task.get_status_display(), "taskId": task.id}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def get_tasks_json(request):
    user = request.user
    project_id = request.GET.get("project_id")

    if project_id:
        # Check if user has access to this project
        project = get_object_or_404(Project, pk=project_id)
        if (
            not user.is_admin
            and user != project.created_by
            and not ProjectMember.objects.filter(project=project, user=user).exists()
        ):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        tasks = Task.objects.filter(project=project)
    else:
        # Get tasks based on user role
        if user.is_admin:
            tasks = Task.objects.all()
        else:
            # Get projects the user is a member of
            user_projects = Project.objects.filter(
                Q(created_by=user) | Q(members=user)
            ).distinct()

            # Get tasks from those projects or assigned to the user
            tasks = Task.objects.filter(
                Q(project__in=user_projects) | Q(assigned_to=user) | Q(created_by=user)
            ).distinct()

    # Format for FullCalendar
    events = []
    for task in tasks:
        color = ""
        if task.status == Task.COMPLETED:
            color = "#28a745"  # Green for completed
        elif task.status == Task.IN_PROGRESS:
            color = "#007bff"  # Blue for in progress
        elif task.status == Task.REVIEW:
            color = "#fd7e14"  # Orange for review
        else:
            color = (
                "#dc3545" if task.is_overdue else "#6c757d"
            )  # Red for overdue, gray for todo

        events.append(
            {
                "id": task.id,
                "title": task.title,
                "start": task.due_date.isoformat(),
                "url": reverse("tasks:detail", kwargs={"pk": task.id}),
                "backgroundColor": color,
                "borderColor": color,
                "textColor": "#fff",
                "extendedProps": {
                    "status": task.get_status_display(),
                    "project": task.project.name,
                    "assignee": (
                        task.assigned_to.username if task.assigned_to else "Unassigned"
                    ),
                },
            }
        )

    return JsonResponse(events, safe=False)


@login_required
def get_tasks_by_date(request):
    """
    API endpoint to get tasks for a specific date
    Used by the calendar view to load tasks for each day
    """
    user = request.user
    date_str = request.GET.get("date")
    project_id = request.GET.get("project_id")

    if not date_str:
        return JsonResponse(
            {"status": "error", "message": "Date parameter is required"}, status=400
        )

    # Parse the date
    try:
        from datetime import datetime

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse(
            {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"},
            status=400,
        )

    # Get the tasks for this date
    if project_id:
        # Check if user has access to this project
        project = get_object_or_404(Project, pk=project_id)
        if (
            not user.is_admin
            and user != project.created_by
            and not ProjectMember.objects.filter(project=project, user=user).exists()
        ):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        tasks = Task.objects.filter(project=project, due_date=date_obj)
    else:
        # Get tasks based on user role
        if user.is_admin:
            tasks = Task.objects.filter(due_date=date_obj)
        else:
            # Get projects the user is a member of
            user_projects = Project.objects.filter(
                Q(created_by=user) | Q(members=user)
            ).distinct()

            # Get tasks from those projects or assigned to the user for the specific date
            tasks = Task.objects.filter(
                Q(project__in=user_projects) | Q(assigned_to=user) | Q(created_by=user),
                due_date=date_obj,
            ).distinct()

    # Format tasks for the response
    tasks_data = []
    for task in tasks:
        tasks_data.append(
            {
                "id": task.id,
                "title": task.title,
                "status": task.get_status_display(),
                "priority": task.get_priority_display(),
                "project": task.project.name,
                "url": reverse("tasks:detail", kwargs={"pk": task.id}),
                "is_completed": task.is_completed,
                "is_overdue": task.is_overdue,
                "assignee": (
                    task.assigned_to.username if task.assigned_to else "Unassigned"
                ),
            }
        )

    return JsonResponse({"date": date_str, "tasks": tasks_data})
