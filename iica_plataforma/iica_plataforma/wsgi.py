"""
WSGI config for iica_plataforma project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iica_plataforma.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
