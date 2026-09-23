def microsoft_flag(request):
    from django.conf import settings
    return {
        'USE_MICROSOFT_AUTH': getattr(settings, 'USE_MICROSOFT_AUTH', False)
    }
