"""
ASGI config for task_management project.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'task_management.settings')
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Import routing from each app
import apps.chat.routing
import apps.notifications.routing
import apps.tasks.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            apps.notifications.routing.websocket_urlpatterns +
            apps.chat.routing.websocket_urlpatterns +
            apps.tasks.routing.websocket_urlpatterns
        )
    ),
})
