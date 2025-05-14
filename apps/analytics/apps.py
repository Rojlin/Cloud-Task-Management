from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.analytics'
    
    def ready(self):
        # Import signals or do other initialization here if needed
        pass
