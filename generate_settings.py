#!/usr/bin/env python3
import os, sys


MODE = sys.argv[1]
DOMAIN = sys.argv[2]
SECRET_KEY = sys.argv[3]


DEBUG = (MODE == "development")
ALLOWED = "['*']" if DEBUG else f"['{DOMAIN}']"
CSRF = "['https://" + DOMAIN + "']" if not DEBUG else "['http://localhost']"


settings = f"""
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = '{SECRET_KEY}'
DEBUG = {str(DEBUG)}
ALLOWED_HOSTS = {ALLOWED}
CSRF_TRUSTED_ORIGINS = {CSRF}


INSTALLED_APPS = [
'secap',
'website_management',
'django.contrib.admin',
'django.contrib.humanize',
'django.contrib.auth',
'django.contrib.contenttypes',
'django.contrib.sessions',
'django.contrib.messages',
'django.contrib.staticfiles',
'channels',
'daphne',
'django_celery_results',
]


ASGI_APPLICATION = 'iica_plataforma.asgi.application'
DATABASES = {{
'default': {{
'ENGINE': 'django.db.backends.postgresql_psycopg2',
'NAME': 'iica_plataforma_db',
'USER': 'postgres',
'PASSWORD': 'iicaPlat',
'HOST': 'db_vm',
'PORT': '5432',
}}
}}


STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
"""


open("iica_plataforma/iica_plataforma/settings.py", "w").write(settings)