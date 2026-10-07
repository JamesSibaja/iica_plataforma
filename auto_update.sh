#!/bin/bash

set -Eeuo pipefail


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

COMPOSE="docker compose"


LOCK_FILE="/var/lock/iica-plataforma-deploy.lock"


exec 9>"$LOCK_FILE"


if ! flock -n 9; then

    echo "Ya existe otro despliegue en ejecución."

    exit 0

fi


echo ""
echo "========================================="
echo " IICA Plataforma - Auto Deploy"
echo " $(date)"
echo "========================================="
echo ""


# =========================================================
# GIT
# =========================================================

echo ">>> Actualizando Git..."


git fetch origin main


LOCAL_COMMIT="$(git rev-parse HEAD)"

REMOTE_COMMIT="$(git rev-parse origin/main)"


if [[ "$LOCAL_COMMIT" == "$REMOTE_COMMIT" ]]; then

    echo ">>> No hay cambios."

    exit 0

fi


echo ">>> Cambios detectados."

echo "Local : $LOCAL_COMMIT"

echo "Remote: $REMOTE_COMMIT"


# =========================================================
# BACKUP DATABASE
# =========================================================

echo ""
echo ">>> Creando respaldo de PostgreSQL..."


BACKUP_DIR="$SCRIPT_DIR/backups"

mkdir -p "$BACKUP_DIR"


TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"


$COMPOSE exec -T db_vm \
    pg_dump \
    -U postgres \
    -d iica_plataforma_db \
    > "$BACKUP_DIR/db_$TIMESTAMP.sql"


# Mantener últimos 14 backups

find "$BACKUP_DIR" \
    -type f \
    -name "db_*.sql" \
    -printf '%T@ %p\n' |
    sort -nr |
    awk 'NR>14 {print $2}' |
    xargs -r rm -f


# =========================================================
# UPDATE SOURCE
# =========================================================

echo ""
echo ">>> Actualizando código..."


git reset --hard origin/main


# =========================================================
# REGENERATE CONFIG
# =========================================================

if [[ ! -f .env ]]; then

    echo "ERROR: .env no existe."

    exit 1

fi


set -a

source .env

set +a


python3 scripts/generate_nginx_conf.py \
    "$MODE" \
    "$DOMAIN" \
    $(if [[ "$MODE" == "production" && -f "letsencrypt/conf/live/$DOMAIN/fullchain.pem" ]]; then echo "--with-ssl"; fi)


# =========================================================
# BUILD
# =========================================================

echo ""
echo ">>> Construyendo imágenes..."


$COMPOSE build


# =========================================================
# DATABASE
# =========================================================

echo ""
echo ">>> Iniciando PostgreSQL y Redis..."


$COMPOSE up -d db_vm redis_vm


until $COMPOSE exec -T db_vm \
    pg_isready \
    -U postgres \
    -d iica_plataforma_db \
    >/dev/null 2>&1
do

    sleep 2

done


# =========================================================
# MIGRATIONS
# =========================================================

echo ""
echo ">>> Aplicando migraciones..."


$COMPOSE run --rm -T gunicorn_vm \
    python manage.py migrate --noinput


$COMPOSE run --rm -T gunicorn_vm \
    python manage.py collectstatic --noinput


# =========================================================
# DEPLOY
# =========================================================

echo ""
echo ">>> Reiniciando aplicación..."


$COMPOSE up -d \
    gunicorn_vm \
    daphne_vm \
    celery_vm \
    celery_beat_vm \
    nginx_vm


# =========================================================
# VERIFY
# =========================================================

sleep 10


echo ""
echo ">>> Estado final:"


$COMPOSE ps


echo ""
echo "========================================="
echo " DEPLOY COMPLETADO"
echo "========================================="