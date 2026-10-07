#!/bin/bash

set -Eeuo pipefail


# =========================================================
# IICA Plataforma
# Setup
# =========================================================


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"


COMPOSE="docker compose"


echo ""
echo "========================================="
echo " IICA Plataforma - Setup"
echo "========================================="
echo ""


# =========================================================
# INPUTS
# =========================================================

read -rp "¿Modo producción? (s/n): " MODE_INPUT


if [[ "$MODE_INPUT" =~ ^[sS]$ ]]; then

    MODE="production"

    DEBUG="False"

    read -rp "Dominio: " DOMAIN

    read -rp "Correo para Let's Encrypt: " EMAIL

    if [[ -z "$DOMAIN" ]]; then
        echo "ERROR: el dominio es obligatorio."
        exit 1
    fi

    if [[ -z "$EMAIL" ]]; then
        echo "ERROR: el correo es obligatorio."
        exit 1
    fi

else

    MODE="development"

    DEBUG="True"

    DOMAIN="localhost"

    EMAIL="admin@localhost"

fi


# =========================================================
# SUPERUSER
# =========================================================

read -rsp "Contraseña del superusuario Django: " SUPERUSER_PASSWORD

echo ""


if [[ -z "$SUPERUSER_PASSWORD" ]]; then

    echo "ERROR: la contraseña no puede estar vacía."

    exit 1

fi


# =========================================================
# ENVIRONMENT
# =========================================================

ENV_FILE="$SCRIPT_DIR/.env"


if [[ -f "$ENV_FILE" ]]; then

    echo ""
    echo ">>> Existe .env; conservando secretos existentes."

    set -a

    source "$ENV_FILE"

    set +a

fi


SECRET_KEY="${SECRET_KEY:-}"

DB_PASSWORD="${DB_PASSWORD:-}"


if [[ -z "$SECRET_KEY" ]]; then

    SECRET_KEY="$(openssl rand -hex 32)"

fi


if [[ -z "$DB_PASSWORD" ]]; then

    DB_PASSWORD="$(openssl rand -hex 32)"

fi


cat > "$ENV_FILE" <<EOF
MODE=$MODE
DEBUG=$DEBUG

DOMAIN=$DOMAIN
EMAIL=$EMAIL

SECRET_KEY=$SECRET_KEY
DB_PASSWORD=$DB_PASSWORD

USE_MICROSOFT_AUTH=${USE_MICROSOFT_AUTH:-False}

MICROSOFT_CLIENT_ID=${MICROSOFT_CLIENT_ID:-}
MICROSOFT_CLIENT_SECRET=${MICROSOFT_CLIENT_SECRET:-}
MICROSOFT_TENANT_ID=${MICROSOFT_TENANT_ID:-}
EOF


chmod 600 "$ENV_FILE"


# =========================================================
# DIRECTORIES
# =========================================================

mkdir -p \
    "$SCRIPT_DIR/letsencrypt/www" \
    "$SCRIPT_DIR/letsencrypt/conf/live"


chmod 755 \
    "$SCRIPT_DIR/letsencrypt" \
    "$SCRIPT_DIR/letsencrypt/www" \
    "$SCRIPT_DIR/letsencrypt/conf"


# =========================================================
# NGINX INITIAL
# =========================================================

echo ""
echo ">>> Generando Nginx inicial..."


python3 scripts/generate_nginx_conf.py \
    "$MODE" \
    "$DOMAIN"


# =========================================================
# STOP OLD STACK
# =========================================================

echo ""
echo ">>> Deteniendo stack anterior..."


$COMPOSE down --remove-orphans || true


# =========================================================
# BUILD
# =========================================================

echo ""
echo ">>> Construyendo imágenes..."


$COMPOSE build


# =========================================================
# START
# =========================================================

echo ""
echo ">>> Iniciando servicios..."


$COMPOSE up -d


# =========================================================
# WAIT DATABASE
# =========================================================

echo ""
echo ">>> Esperando PostgreSQL..."


until $COMPOSE exec -T db_vm \
    pg_isready \
    -U postgres \
    -d iica_plataforma_db \
    >/dev/null 2>&1
do

    sleep 2

done


echo ">>> PostgreSQL listo."


# =========================================================
# MIGRATIONS
# =========================================================

echo ""
echo ">>> Aplicando migraciones..."


$COMPOSE exec -T gunicorn_vm \
    python manage.py makemigrations --noinput


$COMPOSE exec -T gunicorn_vm \
    python manage.py migrate --noinput


# =========================================================
# STATIC
# =========================================================

$COMPOSE exec -T gunicorn_vm \
    python manage.py collectstatic --noinput


# =========================================================
# SUPERUSER
# =========================================================

echo ""
echo ">>> Verificando superusuario..."


export SUPERUSER_PASSWORD


$COMPOSE exec -T \
    -e SUPERUSER_PASSWORD="$SUPERUSER_PASSWORD" \
    gunicorn_vm \
    python manage.py shell <<'PY'

import os

from django.contrib.auth import get_user_model


User = get_user_model()

password = os.environ["SUPERUSER_PASSWORD"]


if not User.objects.filter(is_superuser=True).exists():

    User.objects.create_superuser(
        "admin",
        os.environ.get("EMAIL", "admin@localhost"),
        password
    )

    print("Superusuario creado.")

else:

    print("Ya existe un superusuario.")

PY


unset SUPERUSER_PASSWORD


# =========================================================
# PRODUCTION SSL
# =========================================================

if [[ "$MODE" == "production" ]]; then

    echo ""
    echo "========================================="
    echo " CONFIGURANDO SSL"
    echo "========================================="
    echo ""


    # Nginx está actualmente en HTTP.
    # Esto permite que Let's Encrypt pueda hacer HTTP-01.

    sudo "$SCRIPT_DIR/init-letsencrypt.sh" \
        "$DOMAIN" \
        "$EMAIL"


    echo ""
    echo ">>> Generando Nginx HTTPS..."


    python3 scripts/generate_nginx_conf.py \
        "$MODE" \
        "$DOMAIN" \
        --with-ssl


    echo ""
    echo ">>> Validando configuración Nginx..."


    $COMPOSE exec -T nginx_vm nginx -t


    echo ""
    echo ">>> Reiniciando Nginx..."


    $COMPOSE restart nginx_vm

fi


# =========================================================
# CRON
# =========================================================

echo ""
echo ">>> Configurando actualización automática..."


sudo "$SCRIPT_DIR/install-cron.sh"


# =========================================================
# FINAL
# =========================================================

echo ""
echo "========================================="
echo " SETUP COMPLETADO"
echo "========================================="
echo ""


if [[ "$MODE" == "production" ]]; then

    echo "URL:"
    echo "https://$DOMAIN"

else

    echo "URL:"
    echo "http://localhost"

fi


echo ""