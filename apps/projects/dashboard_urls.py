from django.urls import path
from . import views
from .workflow_views import WorkflowDiagramsView

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='index'),
    path('workflows/', WorkflowDiagramsView.as_view(), name='workflows'),
]
