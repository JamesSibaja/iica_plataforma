from django.apps import AppConfig

class WebsiteManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'website_management'

    def ready(self):
        import website_management.signals