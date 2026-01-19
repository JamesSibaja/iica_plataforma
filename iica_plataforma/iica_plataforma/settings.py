import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'xqMZHzn00ei8kshBbzWWKC1Ao+IVj6iF/+7enAeLpso='

DEBUG = True

ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['http://localhost:80']

INSTALLED_APPS = [
    'secap',
    'website_management',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django_extensions',
    'colorfield',
    'channels',
    'daphne',
    'django.contrib.staticfiles',
    'django_celery_results',
]

ASGI_APPLICATION = 'iica_plataforma.asgi.application'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'iica_plataforma.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'iica_plataforma.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'iica_plataforma_db',
        'USER': 'postgres',
        'PASSWORD': 'iicaPlat',
        'HOST': 'db_vm',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c timezone=UTC',
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-eu'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True

STATIC_URL = '/static/'

if DEBUG:
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, 'static'),
        os.path.join(BASE_DIR, 'secap', 'static'),
    ]
    STATIC_ROOT = None
else:
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, 'static'), 
    ]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

CELERY_BROKER_URL = 'redis://redis_vm:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis_vm:6379/0'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('redis_vm', 6379)],
        },
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'channels': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
