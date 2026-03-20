#!/bin/bash
set -e

echo "========================================="
echo " IICA Plataforma - Setup"
echo "========================================="

# -------------------------
# INPUTS
# -------------------------
read -p "¿Modo producción? (s/n): " mode
read -p "Ingresa tu dominio (vacío = localhost): " domain
read -p "Ingresa tu correo electrónico para SSL: " email
read -s -p "Ingresa la contraseña del superusuario Django: " password
echo

# -------------------------
# MODE
# -------------------------
if [[ "$mode" == "s" || "$mode" == "S" ]]; then
    MODE="production"
    DEBUG=False
    DOMAIN=${domain:? "En producción el dominio es obligatorio"}
    ALLOWED_HOSTS="['$DOMAIN']"
    CSRF_TRUSTED_ORIGINS="['https://$DOMAIN']"
else
    MODE="development"
    DEBUG=True
    DOMAIN="localhost"
    ALLOWED_HOSTS="['*']"
    CSRF_TRUSTED_ORIGINS="['http://localhost']"
fi

EMAIL=${email:-admin@localhost}
PASSWORD=${password:? "La contraseña no puede estar vacía"}

# -------------------------
# GENERAR SECRETOS
# -------------------------
echo "Generando secretos seguros..."
SECRET_KEY=$(openssl rand -base64 48)
DB_PASSWORD=$(openssl rand -base64 32)

# -------------------------
# .ENV
# -------------------------
echo "Generando archivo .env..."

cat > .env <<EOF
MODE=$MODE
DOMAIN=$DOMAIN
EMAIL=$EMAIL
DB_PASSWORD=$DB_PASSWORD

USE_MICROSOFT_AUTH=False
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
EOF

echo "Modo: $MODE"
echo "Dominio: $DOMAIN"

# -------------------------
# CONTEXT PROCESSOR
# -------------------------
echo "Creando context processor..."

mkdir -p iica_plataforma/iica_plataforma

cat > iica_plataforma/iica_plataforma/context_processors.py <<EOF
def microsoft_flag(request):
    from django.conf import settings
    return {
        'USE_MICROSOFT_AUTH': getattr(settings, 'USE_MICROSOFT_AUTH', False)
    }
EOF

# -------------------------
# DJANGO SETTINGS
# -------------------------
echo "Generando settings.py..."

cat > iica_plataforma/iica_plataforma/settings.py <<EOL
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "$SECRET_KEY"
DEBUG = $DEBUG

ALLOWED_HOSTS = $ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = $CSRF_TRUSTED_ORIGINS

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# -------------------------
# MICROSOFT AUTH FLAG
# -------------------------
USE_MICROSOFT_AUTH = os.getenv("USE_MICROSOFT_AUTH") == "True"

# -------------------------
# APPS
# -------------------------
INSTALLED_APPS = [

    # Core Django
    'daphne',  
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',

    'django.contrib.staticfiles',

    # Third-party
    'channels',
    'django_celery_results',

    # Apps propias
    'iica_coworking',
    'secap',
    'website_management',
]

if USE_MICROSOFT_AUTH:
    INSTALLED_APPS += [
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        'allauth.socialaccount.providers.microsoft',
    ]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',  

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware', 

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -------------------------
# AUTH
# -------------------------
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

if USE_MICROSOFT_AUTH:
    AUTHENTICATION_BACKENDS.append(
        'allauth.account.auth_backends.AuthenticationBackend'
    )

# -------------------------
# MICROSOFT CONFIG
# -------------------------
if USE_MICROSOFT_AUTH:
    SOCIALACCOUNT_PROVIDERS = {
        "microsoft": {
            "APP": {
                "client_id": os.getenv("MICROSOFT_CLIENT_ID"),
                "secret": os.getenv("MICROSOFT_CLIENT_SECRET"),
                "key": ""
            }
        }
    }

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# -------------------------
# TEMPLATES (IMPORTANTE)
# -------------------------
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',  # NECESARIO PARA ALLAUTH
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'iica_plataforma.context_processors.microsoft_flag',
        ],
    },
}]

# -------------------------
# DATABASE
# -------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'iica_plataforma_db',
        'USER': 'postgres',
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': 'db_vm',
        'PORT': '5432',
    }
}

# -------------------------
# RESTO
# -------------------------
LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

CELERY_BROKER_URL = 'redis://redis_vm:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis_vm:6379/0'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [('redis_vm', 6379)]},
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
EOL

# -------------------------
# NGINX
# -------------------------
echo "Generando configuración inicial de Nginx..."
python3 scripts/generate_nginx_conf.py "$MODE" "$DOMAIN"

# -------------------------
# DOCKER UP
# -------------------------
echo "Levantando contenedores..."

if [ "$MODE" = "production" ]; then
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
else
  docker compose --env-file .env up -d --build
fi

# -------------------------
# ESPERAR DB
# -------------------------
echo "Esperando base de datos..."
sleep 5

# -------------------------
# MIGRACIONES
# -------------------------
docker compose exec -T gunicorn_vm python manage.py makemigrations
docker compose exec -T gunicorn_vm python manage.py migrate --run-syncdb

# -------------------------
# ALLAUTH AUTO
# -------------------------
docker compose exec -T gunicorn_vm python manage.py shell < scripts/setup_allauth.py || true

# -------------------------
# STATIC
# -------------------------
if [ "$MODE" = "production" ]; then
    docker compose exec -T gunicorn_vm python manage.py collectstatic --noinput
fi

# -------------------------
# SUPERUSER
# -------------------------
docker compose run --rm \
  -e DJANGO_SUPERUSER_EMAIL="$EMAIL" \
  -e DJANGO_SUPERUSER_PASSWORD="$PASSWORD" \
  gunicorn_vm \
  python /app/scripts/create_superuser.py

# -------------------------
# SSL
# -------------------------
if [[ "$MODE" == "production" ]]; then

    echo "Configurando SSL..."

    if [[ ! -f /etc/ssl/certs/dhparam.pem ]]; then
        sudo mkdir -p /etc/ssl/certs
        sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
    fi

    sudo ./init-letsencrypt.sh "$DOMAIN" "$EMAIL" || echo "⚠️ SSL pendiente"

    python3 scripts/generate_nginx_conf.py "$MODE" "$DOMAIN" --with-ssl
    docker compose restart nginx_vm

    echo "Configurando auto deploy..."

    chmod +x scripts/auto_update.sh

    CRON_JOB="0 2 * * * $(pwd)/scripts/auto_update.sh"
    (crontab -l 2>/dev/null | grep -v auto_update.sh; echo "$CRON_JOB") | crontab -
fi

# -------------------------
# AUTO-RESTART DOCKER
# -------------------------
echo "Configurando auto-restart..."
docker update --restart unless-stopped $(docker ps -q) || true

echo "========================================="
echo " Setup finalizado correctamente "
echo "========================================="