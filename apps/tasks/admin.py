from django.contrib import admin

from .models import Task, TaskAttachment, TaskComment


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 1


class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 1


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "assigned_to",
        "status",
        "priority",
        "due_date",
        "created_at",
    )
    list_filter = ("status", "priority", "project", "due_date")
    search_fields = ("title", "description", "assigned_to__username")
    inlines = [TaskCommentInline, TaskAttachmentInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin():
            return qs
        # Filter tasks to only show those from projects the user is a member of
        return qs.filter(project__members=request.user)


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "created_at")
    list_filter = ("created_at", "user")
    search_fields = ("comment", "task__title", "user__username")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin():
            return qs
        # Filter comments to only show those from tasks in projects the user is a member of
        return qs.filter(task__project__members=request.user)


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ("task", "file_name", "uploaded_by", "uploaded_at")
    list_filter = ("uploaded_at", "uploaded_by")
    search_fields = ("file_name", "task__title", "uploaded_by__username")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin():
            return qs
        # Filter attachments to only show those from tasks in projects the user is a member of
        return qs.filter(task__project__members=request.user)
