"""
URL configuration for task_management project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

# Customize admin site
admin.site.site_header = "CollaboraSync Admin"
admin.site.site_title = "CollaboraSync Portal"
admin.site.index_title = "Welcome to CollaboraSync Admin Portal"
admin.site.site_url = "/dashboard/"

urlpatterns = [
    # Redirect Django admin paths to our custom admin
    path(
        "admin/analytics/analyticssnapshot/",
        RedirectView.as_view(url="/accounts/admin/"),
        name="admin_analytics_redirect",
    ),
    path(
        "admin/analytics/",
        RedirectView.as_view(url="/accounts/admin/"),
        name="admin_analytics_index_redirect",
    ),
    path(
        "admin/",
        RedirectView.as_view(url="/accounts/admin/"),
        name="admin_index_redirect",
    ),
    # Original Django admin - hidden but still accessible for superusers if needed
    path("django-admin/", admin.site.urls),
    # Main application URLs
    path("", RedirectView.as_view(url="/dashboard/"), name="home"),
    path("accounts/", include("apps.accounts.urls")),
    path("projects/", include("apps.projects.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("chat/", include("apps.chat.urls")),
    path("dashboard/", include("apps.projects.dashboard_urls")),
    path("analytics/", include("apps.analytics.urls")),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
