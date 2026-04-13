from django.apps import AppConfig


class WebsiteManagementConfig(AppConfig):
    name = 'website_management'

def ready(self):
    import website_management.signals
