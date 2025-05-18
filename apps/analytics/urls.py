from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    # Dashboard for analytics
    path("", views.analytics_dashboard, name="dashboard"),
    # Project analytics
    path("projects/", views.project_analytics, name="project_analytics"),
    path(
        "projects/<int:project_id>/",
        views.project_detail_analytics,
        name="project_detail_analytics",
    ),
    # User productivity
    path("productivity/", views.productivity_analytics, name="productivity_analytics"),
    path(
        "productivity/<int:user_id>/",
        views.user_productivity_detail,
        name="user_productivity_detail",
    ),
    # Task analytics
    path("tasks/", views.task_analytics, name="task_analytics"),
    # Analytics Snapshots
    path("snapshots/", views.analytics_snapshots, name="analytics_snapshots"),
    # Report management
    path("reports/", views.report_list, name="report_list"),
    path("reports/create/", views.report_create, name="report_create"),
    path("reports/<int:report_id>/", views.report_detail, name="report_detail"),
    path(
        "reports/<int:report_id>/generate/",
        views.generate_report,
        name="generate_report",
    ),
    path(
        "reports/<int:report_id>/download/<int:file_id>/",
        views.download_report,
        name="download_report",
    ),
    # AJAX endpoints for charts
    path(
        "api/chart/tasks-by-status/",
        views.tasks_by_status_chart,
        name="tasks_by_status_chart",
    ),
    path(
        "api/chart/tasks-by-priority/",
        views.tasks_by_priority_chart,
        name="tasks_by_priority_chart",
    ),
    path(
        "api/chart/completion-time-trend/",
        views.completion_time_trend_chart,
        name="completion_time_trend_chart",
    ),
    path(
        "api/chart/user-productivity/",
        views.user_productivity_chart,
        name="user_productivity_chart",
    ),
    path(
        "api/chart/project-progress/",
        views.project_progress_chart,
        name="project_progress_chart",
    ),
]
