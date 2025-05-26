from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from apps.accounts.models import User, UserProfile
from apps.notifications.models import Notification
from apps.tasks.models import Task

from .forms import (
    ProjectFilterForm,
    ProjectForm,
    ProjectMemberForm,
    ProjectMemberInviteForm,
)
from .models import Project, ProjectMember


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard view showing overview of projects and tasks
    """

    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user's projects
        if user.is_admin():
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(
                Q(created_by=user) | Q(members=user)
            ).distinct()

        # Get user's tasks
        if user.is_admin():
            tasks = Task.objects.all()
        else:
            tasks = Task.objects.filter(
                Q(created_by=user) | Q(assigned_to=user) | Q(project__in=projects)
            ).distinct()

        # Total counts for main stat cards
        context["total_projects"] = projects.count()
        context["tasks_completed"] = tasks.filter(status=Task.COMPLETED).count()

        # Recent projects
        context["recent_projects"] = projects.order_by("-created_at")[:5]

        # Recent tasks
        context["recent_tasks"] = tasks.order_by("-updated_at")[:10]
        context["today"] = timezone.now().date()

        # Tasks by priority for charts
        context["tasks_high_priority"] = tasks.filter(
            priority__in=[Task.HIGH, Task.URGENT]
        ).count()
        context["tasks_medium_priority"] = tasks.filter(priority=Task.MEDIUM).count()
        context["tasks_low_priority"] = tasks.filter(priority=Task.LOW).count()
        context["tasks_no_priority"] = 0  # Default value if needed

        # Tasks by status
        context["todo_tasks"] = tasks.filter(status=Task.TODO).count()
        context["in_progress_tasks"] = tasks.filter(status=Task.IN_PROGRESS).count()
        context["review_tasks"] = tasks.filter(status=Task.REVIEW).count()
        context["completed_tasks"] = tasks.filter(status=Task.COMPLETED).count()

        # Projects by status
        context["planning_projects"] = projects.filter(status=Project.PLANNING).count()
        context["active_projects"] = projects.filter(status=Project.IN_PROGRESS).count()
        context["on_hold_projects"] = projects.filter(status=Project.ON_HOLD).count()
        context["completed_projects"] = projects.filter(
            status=Project.COMPLETED
        ).count()

        # Overdue items
        context["overdue_tasks"] = (
            tasks.filter(due_date__lt=timezone.now().date())
            .exclude(status=Task.COMPLETED)
            .count()
        )

        context["overdue_projects"] = (
            projects.filter(end_date__lt=timezone.now().date())
            .exclude(status__in=[Project.COMPLETED, Project.CANCELLED])
            .count()
        )

        # Upcoming deadlines (next 7 days)
        next_week = timezone.now().date() + timezone.timedelta(days=7)
        context["upcoming_tasks"] = tasks.filter(
            due_date__range=[timezone.now().date(), next_week],
            status__in=[Task.TODO, Task.IN_PROGRESS, Task.REVIEW],
        ).order_by("due_date")[:5]

        context["upcoming_projects"] = projects.filter(
            end_date__range=[timezone.now().date(), next_week],
            status__in=[Project.PLANNING, Project.IN_PROGRESS],
        ).order_by("end_date")[:5]

        context["title"] = "Dashboard"
        return context


class ProjectAccessMixin(UserPassesTestMixin):
    """
    Mixin to check if user has access to a project
    """

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False

        # Check if admin first
        if self.request.user.is_admin():
            return True

        # Get project from kwargs
        project_id = self.kwargs.get("pk") or self.kwargs.get("project_id")
        if not project_id:
            return True  # No project to check against (for list views)

        project = get_object_or_404(Project, pk=project_id)

        # Check if user is project creator
        if project.created_by == self.request.user:
            return True

        # Check if user is a project member
        return ProjectMember.objects.filter(
            project=project, user=self.request.user
        ).exists()


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        form = ProjectFilterForm(self.request.GET)

        # Filter based on user role
        user = self.request.user
        if not user.is_admin():
            queryset = queryset.filter(Q(created_by=user) | Q(members=user)).distinct()

        # Apply filters if form is valid
        if form.is_valid():
            status = form.cleaned_data.get("status")
            priority = form.cleaned_data.get("priority")
            name = form.cleaned_data.get("name")

            if status:
                queryset = queryset.filter(status=status)
            if priority:
                queryset = queryset.filter(priority=priority)
            if name:
                queryset = queryset.filter(name__icontains=name)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = ProjectFilterForm(self.request.GET)
        context["title"] = "Projects"

        # Add counts for dashboard
        user = self.request.user
        if user.is_admin():
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(
                Q(created_by=user) | Q(members=user)
            ).distinct()

        context["total_projects"] = projects.count()
        context["active_projects"] = projects.filter(
            status__in=[Project.PLANNING, Project.IN_PROGRESS]
        ).count()
        context["completed_projects"] = projects.filter(
            status=Project.COMPLETED
        ).count()
        context["overdue_projects"] = (
            projects.filter(end_date__lt=timezone.now().date())
            .exclude(status__in=[Project.COMPLETED, Project.CANCELLED])
            .count()
        )

        return context


class ProjectCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/create.html"
    success_url = reverse_lazy("projects:list")

    def test_func(self):
        # Only admin, project managers, and leaders can create projects
        user = self.request.user
        return user.is_admin() or user.is_project_manager or user.is_leader

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        # Add the creator as a project member with their role
        user_role = self.request.user.userprofile.role
        project_role = ProjectMember.TEAM_MEMBER  # Default

        if user_role == UserProfile.PROJECT_MANAGER:
            project_role = ProjectMember.PROJECT_MANAGER
        elif user_role == UserProfile.LEADER:
            project_role = ProjectMember.LEADER

        ProjectMember.objects.create(
            project=self.object, user=self.request.user, role=project_role
        )

        # Create notifications for all admins and project managers about the new project
        admins_and_pms = (
            User.objects.filter(
                Q(userprofile__role=UserProfile.ADMIN)
                | Q(userprofile__role=UserProfile.PROJECT_MANAGER)
            )
            .exclude(id=self.request.user.id)
            .distinct()
        )

        for user in admins_and_pms:
            Notification.objects.create(
                user=user,
                title="New Project Created",
                message=f"{self.request.user.username} created a new project: {self.object.name}",
                link=reverse("projects:detail", kwargs={"pk": self.object.id}),
                notification_type="project_created",
            )

        # Send notification to channel layer for real-time updates
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()

        for user in admins_and_pms:
            notification_group_name = f"notifications_{user.id}"
            async_to_sync(channel_layer.group_send)(
                notification_group_name,
                {
                    "type": "notification_message",
                    "message": {
                        "title": "New Project Created",
                        "content": f"{self.request.user.username} created a new project: {self.object.name}",
                        "link": reverse(
                            "projects:detail", kwargs={"pk": self.object.id}
                        ),
                    },
                },
            )

        messages.success(
            self.request, f'Project "{self.object.name}" created successfully.'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Project"
        context["action"] = "Create"
        return context


class ProjectDetailView(LoginRequiredMixin, ProjectAccessMixin, DetailView):
    model = Project
    template_name = "projects/detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()

        # Get tasks for the project
        context["tasks"] = Task.objects.filter(project=project).order_by("-created_at")

        # Get project members
        context["members"] = ProjectMember.objects.filter(project=project)

        # Get task counts by status
        task_counts = (
            Task.objects.filter(project=project)
            .values("status")
            .annotate(count=Count("status"))
        )
        status_counts = {item["status"]: item["count"] for item in task_counts}

        context["task_counts"] = {
            "todo": status_counts.get(Task.TODO, 0),
            "in_progress": status_counts.get(Task.IN_PROGRESS, 0),
            "review": status_counts.get(Task.REVIEW, 0),
            "completed": status_counts.get(Task.COMPLETED, 0),
        }

        context["title"] = f"Project: {project.name}"
        return context


class ProjectUpdateView(LoginRequiredMixin, ProjectAccessMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/edit.html"

    def test_func(self):
        if not super().test_func():
            return False

        # Only admin, project creator, project managers, and leaders can edit projects
        user = self.request.user
        project = self.get_object()

        if user.is_admin() or project.created_by == user:
            return True

        # Check if user is a project manager or leader for this project
        member = ProjectMember.objects.filter(project=project, user=user).first()
        return member and member.role in [
            ProjectMember.PROJECT_MANAGER,
            ProjectMember.LEADER,
        ]

    def get_success_url(self):
        return reverse("projects:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Project "{self.object.name}" updated successfully.'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Project: {self.object.name}"
        context["action"] = "Update"
        return context


class ProjectDeleteView(LoginRequiredMixin, ProjectAccessMixin, DeleteView):
    model = Project
    template_name = "projects/delete.html"
    success_url = reverse_lazy("projects:list")
    context_object_name = "project"

    def test_func(self):
        if not super().test_func():
            return False

        # Only admin or project creator can delete projects
        user = self.request.user
        project = self.get_object()

        return user.is_admin() or project.created_by == user

    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        messages.success(
            self.request, f'Project "{project.name}" deleted successfully.'
        )
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Delete Project: {self.object.name}"
        return context


class ProjectMemberListView(LoginRequiredMixin, ProjectAccessMixin, ListView):
    model = ProjectMember
    template_name = "projects/members.html"
    context_object_name = "members"

    def get_queryset(self):
        self.project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        return ProjectMember.objects.filter(project=self.project)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        context["title"] = f"Project Members: {self.project.name}"
        return context


class ProjectMemberCreateView(LoginRequiredMixin, ProjectAccessMixin, CreateView):
    model = ProjectMember
    form_class = ProjectMemberForm
    template_name = "projects/member_form.html"

    def test_func(self):
        if not super().test_func():
            return False

        # Only admin, project creator, project managers can add members
        user = self.request.user
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])

        if user.is_admin() or project.created_by == user:
            return True

        # Check if user is a project manager for this project
        member = ProjectMember.objects.filter(project=project, user=user).first()
        return member and member.role == ProjectMember.PROJECT_MANAGER

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])

        # Exclude users already in the project
        existing_users = project.members.all()
        form.fields["user"].queryset = User.objects.exclude(id__in=existing_users)

        return form

    def form_valid(self, form):
        form.instance.project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        response = super().form_valid(form)

        # Create notification for the added user
        Notification.objects.create(
            user=form.instance.user,
            title="Added to Project",
            message=f'You have been added to project "{form.instance.project.name}" as {form.instance.get_role_display()}',
            link=reverse("projects:detail", kwargs={"pk": form.instance.project.id}),
        )

        messages.success(
            self.request,
            f"{form.instance.user.username} added to project successfully.",
        )
        return response

    def get_success_url(self):
        return reverse(
            "projects:members", kwargs={"project_id": self.kwargs["project_id"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        context["project"] = project
        context["title"] = f"Add Member to {project.name}"
        context["action"] = "Add"
        return context


class ProjectMemberUpdateView(LoginRequiredMixin, ProjectAccessMixin, UpdateView):
    model = ProjectMember
    form_class = ProjectMemberForm
    template_name = "projects/member_form.html"

    def test_func(self):
        if not super().test_func():
            return False

        # Only admin, project creator, project managers can update members
        user = self.request.user
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])

        if user.is_admin() or project.created_by == user:
            return True

        # Check if user is a project manager for this project
        member = ProjectMember.objects.filter(project=project, user=user).first()
        return member and member.role == ProjectMember.PROJECT_MANAGER

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Disable changing the user
        form.fields["user"].disabled = True
        return form

    def form_valid(self, form):
        response = super().form_valid(form)

        # Create notification for the updated member
        Notification.objects.create(
            user=form.instance.user,
            title="Project Role Updated",
            message=f'Your role in project "{form.instance.project.name}" has been updated to {form.instance.get_role_display()}',
            link=reverse("projects:detail", kwargs={"pk": form.instance.project.id}),
        )

        messages.success(
            self.request, f"{form.instance.user.username}'s role updated successfully."
        )
        return response

    def get_success_url(self):
        return reverse(
            "projects:members", kwargs={"project_id": self.kwargs["project_id"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        context["project"] = project
        context["title"] = f"Update Member in {project.name}"
        context["action"] = "Update"
        return context


class ProjectMemberDeleteView(LoginRequiredMixin, ProjectAccessMixin, DeleteView):
    model = ProjectMember
    template_name = "projects/member_confirm_delete.html"
    context_object_name = "member"

    def test_func(self):
        if not super().test_func():
            return False

        # Only admin, project creator, project managers can remove members
        user = self.request.user
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        member = self.get_object()

        # Cannot remove self if you're the creator
        if member.user == user and project.created_by == user:
            return False

        if user.is_admin() or project.created_by == user:
            return True

        # Check if user is a project manager for this project
        user_member = ProjectMember.objects.filter(project=project, user=user).first()
        return user_member and user_member.role == ProjectMember.PROJECT_MANAGER

    def get_success_url(self):
        return reverse(
            "projects:members", kwargs={"project_id": self.kwargs["project_id"]}
        )

    def delete(self, request, *args, **kwargs):
        member = self.get_object()

        # Create notification for the removed user
        Notification.objects.create(
            user=member.user,
            title="Removed from Project",
            message=f'You have been removed from project "{member.project.name}"',
            link=None,
        )

        messages.success(
            self.request, f"{member.user.username} removed from project successfully."
        )
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        context["project"] = project
        context["title"] = f"Remove Member from {project.name}"
        return context


class ProjectMemberInviteView(LoginRequiredMixin, ProjectAccessMixin, TemplateView):
    template_name = "projects/member_invite.html"

    def test_func(self):
        if not super().test_func():
            return False

        # Only admin, project creator, project managers can invite members
        user = self.request.user
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])

        if user.is_admin() or project.created_by == user:
            return True

        # Check if user is a project manager for this project
        member = ProjectMember.objects.filter(project=project, user=user).first()
        return member and member.role == ProjectMember.PROJECT_MANAGER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        context["project"] = project
        context["form"] = ProjectMemberInviteForm()
        context["title"] = f"Invite Members to {project.name}"
        return context

    def post(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        form = ProjectMemberInviteForm(request.POST)

        if form.is_valid():
            emails = form.cleaned_data["emails"]
            role = form.cleaned_data["role"]

            existing_users = []
            invited_users = []

            for email in emails:
                user = User.objects.filter(email=email).first()
                if user:
                    # Check if user is already a member
                    if ProjectMember.objects.filter(
                        project=project, user=user
                    ).exists():
                        existing_users.append(email)
                        continue

                    # Add user to project
                    ProjectMember.objects.create(project=project, user=user, role=role)

                    # Create notification
                    Notification.objects.create(
                        user=user,
                        title="Added to Project",
                        message=f'You have been added to project "{project.name}" as {dict(ProjectMember.ROLE_CHOICES)[role]}',
                        link=reverse("projects:detail", kwargs={"pk": project.id}),
                    )

                    invited_users.append(email)

            if invited_users:
                messages.success(
                    request,
                    f"Successfully added {len(invited_users)} members to the project.",
                )

            if existing_users:
                messages.warning(
                    request,
                    f'The following users are already members: {", ".join(existing_users)}',
                )

            return redirect("projects:members", project_id=project.id)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class ProjectMemberApiView(LoginRequiredMixin, View):
    """API endpoint for getting project members"""

    def get(self, request, project_id):
        try:
            project = get_object_or_404(Project, pk=project_id)

            # Check if user has access to the project
            is_member = ProjectMember.objects.filter(
                project=project, user=request.user
            ).exists()
            if not (
                request.user.is_admin()
                or project.created_by == request.user
                or is_member
            ):
                return JsonResponse({"error": "Access denied"}, status=403)

            # Get all members of the project
            members = ProjectMember.objects.filter(project=project).select_related(
                "user"
            )

            # Format the response
            member_list = [
                {
                    "id": member.user.id,
                    "name": member.user.get_full_name() or member.user.username,
                    "username": member.user.username,
                    "role": member.get_role_display(),
                }
                for member in members
            ]

            # Also include project creator if not already in the members list
            if not any(m["id"] == project.created_by.id for m in member_list):
                member_list.append(
                    {
                        "id": project.created_by.id,
                        "name": project.created_by.get_full_name()
                        or project.created_by.username,
                        "username": project.created_by.username,
                        "role": "Creator",
                    }
                )

            return JsonResponse({"members": member_list})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class ProjectStatisticsView(LoginRequiredMixin, ProjectAccessMixin, DetailView):
    model = Project
    template_name = "projects/statistics.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()

        # Get task counts by status
        task_counts = (
            Task.objects.filter(project=project)
            .values("status")
            .annotate(count=Count("status"))
        )
        status_counts = {item["status"]: item["count"] for item in task_counts}

        # Format for chart.js
        status_labels = [
            dict(Task.STATUS_CHOICES)[status]
            for status in [Task.TODO, Task.IN_PROGRESS, Task.REVIEW, Task.COMPLETED]
        ]
        status_data = [
            status_counts.get(Task.TODO, 0),
            status_counts.get(Task.IN_PROGRESS, 0),
            status_counts.get(Task.REVIEW, 0),
            status_counts.get(Task.COMPLETED, 0),
        ]

        # Get tasks by assignee
        assignee_tasks = (
            Task.objects.filter(project=project)
            .values("assigned_to__username")
            .annotate(count=Count("assigned_to"))
        )
        assignee_labels = [
            item["assigned_to__username"] or "Unassigned" for item in assignee_tasks
        ]
        assignee_data = [item["count"] for item in assignee_tasks]

        # Get task completion over time (last 30 days)
        today = timezone.now().date()
        thirty_days_ago = today - timezone.timedelta(days=30)
        completed_tasks = (
            Task.objects.filter(
                project=project,
                status=Task.COMPLETED,
                completed_at__gte=thirty_days_ago,
            )
            .values("completed_at__date")
            .annotate(count=Count("id"))
            .order_by("completed_at__date")
        )

        # Create a dict with all dates in the last 30 days
        date_range = [
            (thirty_days_ago + timezone.timedelta(days=i)).isoformat()
            for i in range(31)
        ]
        completion_data = {date: 0 for date in date_range}

        # Fill in actual completion data
        for item in completed_tasks:
            date = item["completed_at__date"].isoformat()
            completion_data[date] = item["count"]

        timeline_labels = list(completion_data.keys())
        timeline_data = list(completion_data.values())

        context.update(
            {
                "status_labels": status_labels,
                "status_data": status_data,
                "assignee_labels": assignee_labels,
                "assignee_data": assignee_data,
                "timeline_labels": timeline_labels,
                "timeline_data": timeline_data,
                "title": f"Statistics: {project.name}",
            }
        )

        return context
