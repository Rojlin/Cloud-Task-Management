from django.urls import path
from .consumers import TaskConsumer, TaskCommentsConsumer

websocket_urlpatterns = [
    path('ws/tasks/kanban/', TaskConsumer.as_asgi()),
    path('ws/tasks/<int:task_id>/comments/', TaskCommentsConsumer.as_asgi()),
]