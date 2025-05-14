from django.contrib import admin
from .models import (
    ReportType, 
    Report, 
    ReportFile, 
    AnalyticsSnapshot, 
    UserProductivity, 
    TaskCompletionTime
)

@admin.register(ReportType)
class ReportTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    ordering = ('name',)

class ReportFileInline(admin.TabularInline):
    model = ReportFile
    extra = 0
    readonly_fields = ('created_at', 'size')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'user', 'project', 'format', 'frequency', 'last_generated', 'is_active')
    list_filter = ('report_type', 'format', 'frequency', 'is_active')
    search_fields = ('title', 'description', 'user__username', 'project__name')
    inlines = [ReportFileInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'report_type', 'user', 'project')
        }),
        ('Configuration', {
            'fields': ('format', 'frequency', 'parameters', 'is_active')
        }),
        ('Schedule', {
            'fields': ('last_generated', 'next_generation')
        }),
    )

@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ('project', 'total_tasks', 'completed_tasks', 'pending_tasks', 'overdue_tasks', 'active_users', 'timestamp')
    list_filter = ('project', 'timestamp')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)

@admin.register(UserProductivity)
class UserProductivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'tasks_assigned', 'tasks_completed', 'activity_score')
    list_filter = ('date', 'user')
    date_hierarchy = 'date'
    search_fields = ('user__username', 'user__email')

@admin.register(TaskCompletionTime)
class TaskCompletionTimeAdmin(admin.ModelAdmin):
    list_display = ('task', 'assigned_date', 'completion_date', 'time_to_complete', 'efficiency_score')
    list_filter = ('assigned_date', 'completion_date')
    date_hierarchy = 'completion_date'
    search_fields = ('task__title',)
    readonly_fields = ('task', 'assigned_date', 'start_date', 'completion_date')
