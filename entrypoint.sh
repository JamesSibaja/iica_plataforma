#!/bin/bash
set -e


# Esperar a la DB
echo "Waiting for Postgres..."
for i in {1..30}; do
if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" >/dev/null 2>&1; then
echo "Postgres is up"
break
fi
echo "Waiting for postgres... ($i)"
sleep 1
done


# Ejecutar migraciones y crear superuser si variables están presentes
python manage.py makemigrations --noinput || true
python manage.py migrate --noinput


# Crear superuser si variables definidas
if [ -n "${DJANGO_SUPERUSER_EMAIL}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
python - <<PY
from django.contrib.auth import get_user_model
User=get_user_model()
if not User.objects.filter(email='${DJANGO_SUPERUSER_EMAIL}').exists():
User.objects.create_superuser('admin','${DJANGO_SUPERUSER_EMAIL}','${DJANGO_SUPERUSER_PASSWORD}')
PY
fi


# Iniciar gunicorn (o el comando que definas en tu Dockerfile)
exec gunicorn iica_plataforma.wsgi:application -b 0.0.0.0:8765