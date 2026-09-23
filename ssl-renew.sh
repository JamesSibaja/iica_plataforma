#!/bin/bash

set -e

# =========================================================
# IICA Plataforma - Renovación SSL
# =========================================================

PROJECT_DIR="/home/usuario/iica_plataforma"
ACME_BIN="/root/.acme.sh/acme.sh"

cd "$PROJECT_DIR" || exit 1

echo "========================================="
echo " RENOVACIÓN / VERIFICACIÓN SSL"
echo " $(date)"
echo "========================================="

# ---------------------------------------------------------
# COMPROBAR ACME.SH
# ---------------------------------------------------------

if [ ! -f "$ACME_BIN" ]; then
    echo "ERROR: acme.sh no está instalado."
    exit 1
fi

# ---------------------------------------------------------
# RENOVAR CERTIFICADOS
# ---------------------------------------------------------

"$ACME_BIN" --cron

# ---------------------------------------------------------
# RECARGAR NGINX
# ---------------------------------------------------------

docker compose exec -T nginx_vm nginx -t

docker compose exec -T nginx_vm nginx -s reload

echo "SSL verificado correctamente."