#!/bin/bash

# Preguntar por el modo de operación
read -p "¿Modo producción? (s/n): " mode
read -p "Ingresa tu dominio (deja vacío para configuración local): " domain
read -p "Ingresa tu correo electrónico para el certificado SSL: " email
read -s -p "Ingresa la contraseña del superusuario de Django: " password
echo

# Determinar el modo
if [[ $mode == "s" || $mode == "S" ]]; then
    MODE="production"
    DEBUG=False
    ALLOWED_HOSTS="['$domain']"
    CSRF_TRUSTED_ORIGINS="['https://$domain']"
else
    MODE="development"
    DEBUG=True
    ALLOWED_HOSTS="['*']"
    CSRF_TRUSTED_ORIGINS="['http://localhost:80']"
fi

# Establecer valores predeterminados
DOMAIN=${domain:-localhost}
EMAIL=${email:-admin@localhost}
PASSWORD=$password

# Exportar la variable de entorno para Docker Compose
export MODE

# Generar SECRET_KEY
SECRET_KEY=$(openssl rand -base64 32)

# Escribir el archivo settings.py
cat <<EOL > iica_plataforma/iica_plataforma/settings.py
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = '$SECRET_KEY'

DEBUG = $DEBUG

ALLOWED_HOSTS = $ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = $CSRF_TRUSTED_ORIGINS

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
EOL

# Configurar entorno virtual y dependencias
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "Python is not installed. Installing Python3..."
    sudo apt-get update
    sudo apt-get install -y python3
    PYTHON_CMD=python3
fi

sudo $PYTHON_CMD -m venv iica_plataforma/venv
source iica_plataforma/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Generar configuración de Nginx
sudo $PYTHON_CMD scripts/generate_nginx_conf.py $MODE $DOMAIN

# Verificar configuración de Nginx
if [[ ! -f nginx.conf ]]; then
    echo "Error: Los archivos de configuración de Nginx no se generaron correctamente."
    exit 1
fi

# Exportar la variable de modo para docker-compose
export MODE=$MODE

if [[ $MODE == "production" ]]; then
    if [ ! -f /etc/ssl/certs/dhparam.pem ]; then
        echo "### Generating dhparam.pem file ..."
        sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
    fi
fi

# Instalar acme.sh si no está instalado
if [ ! -d "$HOME/.acme.sh" ]; then
  echo "### Instalando acme.sh ..."
  curl https://get.acme.sh | sh
fi

# Cargar acme.sh en el PATH
export PATH="$HOME/.acme.sh":$PATH

# Construir imágenes Docker
sudo docker compose build --build-arg MODE=$MODE redis_vm db_vm gunicorn_vm daphne_vm celery_vm nginx_vm

# Inicializar y configurar la base de datos PostgreSQL
sudo docker compose up --no-build -d --no-recreate redis_vm db_vm gunicorn_vm daphne_vm celery_vm
sudo docker compose exec gunicorn_vm python manage.py makemigrations
sudo docker compose exec gunicorn_vm python manage.py migrate

if [[ $MODE == "production" ]]; then
    sudo docker compose exec gunicorn_vm python manage.py collectstatic --noinput
fi

# Exportar las variables de entorno para el superusuario
export DJANGO_SUPERUSER_EMAIL=$EMAIL
export DJANGO_SUPERUSER_PASSWORD=$PASSWORD

sudo docker exec -e DJANGO_SUPERUSER_EMAIL=$DJANGO_SUPERUSER_EMAIL -e DJANGO_SUPERUSER_PASSWORD=$DJANGO_SUPERUSER_PASSWORD $(sudo docker ps -q -f name=gunicorn_vm) python manage.py shell -c "exec(open('/app/scripts/create_superuser.py').read())"

# Iniciar Nginx sin SSL
sudo docker compose up --no-build -d --no-recreate nginx_vm

if [[ $MODE == "production" ]]; then
    sudo ./init-letsencrypt.sh $DOMAIN $EMAIL
    # Regenerar configuración de Nginx para SSL
    sudo $PYTHON_CMD scripts/generate_nginx_conf.py $MODE $DOMAIN --with-ssl
fi

# Iniciar la aplicación
sudo docker compose up --no-build -d --no-recreate redis_vm db_vm gunicorn_vm daphne_vm celery_vm nginx_vm

# Recargar Nginx con la nueva configuración
if [[ $MODE == "production" ]]; then
    sudo docker compose exec nginx_vm nginx -s reload
fi