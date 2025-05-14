from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    # Task URLs
    path('', views.TaskListView.as_view(), name='list'),
    path('create/', views.TaskCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TaskUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.TaskDeleteView.as_view(), name='delete'),
    path('<int:pk>/status/<str:status>/', views.TaskStatusUpdateView.as_view(), name='status_update'),
    path('<int:pk>/priority/<str:priority>/', views.TaskPriorityUpdateView.as_view(), name='priority_update'),
    
    # Task Comment URLs
    path('<int:task_id>/comment/', views.TaskCommentCreateView.as_view(), name='comment_create'),
    path('comment/<int:pk>/delete/', views.TaskCommentDeleteView.as_view(), name='comment_delete'),
    
    # Task Attachment URLs
    path('<int:task_id>/attachment/', views.TaskAttachmentCreateView.as_view(), name='attachment_create'),
    path('attachment/<int:pk>/delete/', views.TaskAttachmentDeleteView.as_view(), name='attachment_delete'),
    
    # Task Kanban View
    path('kanban/', views.TaskKanbanView.as_view(), name='kanban'),
    path('project/<int:project_id>/kanban/', views.ProjectTaskKanbanView.as_view(), name='project_kanban'),
    
    # Task Calendar View
    path('calendar/', views.TaskCalendarView.as_view(), name='calendar'),
    path('project/<int:project_id>/calendar/', views.ProjectTaskCalendarView.as_view(), name='project_calendar'),
    
    # API for AJAX operations
    path('api/update-position/', views.update_task_status, name='update_task_position'),
    path('api/update_status/<int:task_id>/<str:status>/', views.update_task_status_api, name='update_task_status_api'),
    path('api/tasks/', views.get_tasks_json, name='get_tasks_json'),
    path('api/tasks-by-date/', views.get_tasks_by_date, name='get_tasks_by_date'),
]
