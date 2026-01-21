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

export MODE

echo "Modo: $MODE"
echo "Dominio: $DOMAIN"

# -------------------------
# SECRET KEY
# -------------------------
SECRET_KEY=$(openssl rand -base64 48)

# -------------------------
# DJANGO SETTINGS
# -------------------------
echo "Generando settings.py..."

cat > iica_plataforma/iica_plataforma/settings.py <<EOL
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "$SECRET_KEY"
DEBUG = $DEBUG

ALLOWED_HOSTS = $ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = $CSRF_TRUSTED_ORIGINS

# Permite a Django detectar HTTPS detrás de Nginx
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookies seguras en producción
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'channels',
    'daphne',
    'django_celery_results',
    'django.contrib.staticfiles',
    'secap',
    'website_management',
]

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

TEMPLATES = [{
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
}]

ASGI_APPLICATION = 'iica_plataforma.asgi.application'
WSGI_APPLICATION = 'iica_plataforma.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'iica_plataforma_db',
        'USER': 'postgres',
        'PASSWORD': 'iicaPlat',
        'HOST': 'db_vm',
        'PORT': '5432',
    }
}

LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

if DEBUG:
    STATICFILES_DIRS = [BASE_DIR / 'static']
else:
    STATIC_ROOT = BASE_DIR / 'staticfiles'

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

# Elimina warnings W042
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
EOL


# -------------------------
# NGINX CONF
# -------------------------
echo "Generando configuración de Nginx..."
python3 scripts/generate_nginx_conf.py "$MODE" "$DOMAIN"

if [[ ! -f nginx.conf ]]; then
    echo "ERROR: nginx.conf no generado"
    exit 1
fi

# -------------------------
# SSL PREPARATION
# -------------------------

if [[ "$MODE" == "production" ]]; then
    if [[ ! -f /etc/ssl/certs/dhparam.pem ]]; then
        echo "Generando dhparam.pem..."
        sudo mkdir -p /etc/ssl/certs
        sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
    fi
fi


# -------------------------
# ACME.SH
# -------------------------
if [[ "$MODE" == "production" && ! -d "$HOME/.acme.sh" ]]; then
    echo "Instalando acme.sh..."
    curl https://get.acme.sh | sh
fi

export PATH="$HOME/.acme.sh:$PATH"

# -------------------------
# DOCKER BUILD
# -------------------------
echo "Construyendo imágenes Docker..."
sudo docker compose build --build-arg MODE="$MODE"

# -------------------------
# DB + MIGRATIONS
# -------------------------
echo "Iniciando servicios base..."
sudo docker compose up -d redis_vm db_vm gunicorn_vm

echo "Aplicando migraciones..."
docker compose exec gunicorn_vm python manage.py makemigrations
docker compose exec gunicorn_vm python manage.py migrate
if [ "$$MODE" = "production" ]; then \
    docker compose exec gunicorn_vm python manage.py collectstatic --noinput; \
fi


# sudo docker compose run --rm gunicorn_vm python manage.py migrate

# -------------------------
# SUPERUSER
# -------------------------
echo "Creando superusuario..."
sudo docker compose run --rm \
  -e DJANGO_SUPERUSER_EMAIL="$EMAIL" \
  -e DJANGO_SUPERUSER_PASSWORD="$PASSWORD" \
  gunicorn_vm \
  python scripts/create_superuser.py

# -------------------------
# SSL CERTS
# -------------------------
if [[ "$MODE" == "production" ]]; then
    echo "Solicitando certificados SSL..."
    sudo ./init-letsencrypt.sh "$DOMAIN" "$EMAIL"
    python3 scripts/generate_nginx_conf.py "$MODE" "$DOMAIN" --with-ssl
fi

# -------------------------
# START ALL
# -------------------------
echo "Levantando aplicación completa..."
sudo docker compose up -d

if [[ "$MODE" == "production" ]]; then
    sudo docker compose exec nginx_vm nginx -s reload
fi

echo "========================================="
echo " Setup finalizado correctamente "
echo "========================================="
