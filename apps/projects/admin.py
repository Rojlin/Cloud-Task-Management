from django.contrib import admin

from .models import Project, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_by",
        "status",
        "start_date",
        "end_date",
        "created_at",
    )
    list_filter = ("status", "start_date", "end_date")
    search_fields = ("name", "description")
    inlines = [ProjectMemberInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin():
            return qs
        return qs.filter(created_by=request.user)
