#!/bin/bash

set -e

# =========================================================
# IICA Plataforma - Let's Encrypt / acme.sh
# =========================================================

domains=$1
email=$2

if [[ -z "$domains" || -z "$email" ]]; then
    echo "Uso:"
    echo "sudo ./init-letsencrypt.sh dominio correo"
    exit 1
fi

PROJECT_DIR="/home/usuario/iica_plataforma"

ACME_HOME="/root/.acme.sh"
ACME_BIN="$ACME_HOME/acme.sh"

data_path="$PROJECT_DIR/letsencrypt"
data_path_conf="$PROJECT_DIR/letsencrypt/conf"

# =========================================================
# ROOT CHECK
# =========================================================

if [[ "$EUID" -ne 0 ]]; then
    echo "Ejecuta con sudo"
    exit 1
fi

# =========================================================
# DEPENDENCIAS
# =========================================================

apt-get update -qq

apt-get install -y curl cron

systemctl enable cron || true
systemctl start cron || true

# =========================================================
# DIRECTORIOS
# =========================================================

mkdir -p "$data_path/www"
mkdir -p "$data_path_conf/live/$domains"

# =========================================================
# INSTALAR ACME.SH
# =========================================================

if [[ ! -f "$ACME_BIN" ]]; then

    echo ">>> Instalando acme.sh"

    curl https://get.acme.sh | sh

fi

# Volver a comprobar que exista
if [[ ! -f "$ACME_BIN" ]]; then
    echo "ERROR: No se pudo instalar acme.sh"
    exit 1
fi

# =========================================================
# CONFIGURAR ACME.SH
# =========================================================

"$ACME_BIN" --set-default-ca --server zerossl

"$ACME_BIN" \
    --register-account \
    -m "$email" \
    --server zerossl || true

# =========================================================
# EMITIR CERTIFICADO
# =========================================================

echo ">>> Solicitando certificado SSL para $domains..."

"$ACME_BIN" --issue \
    --webroot "$data_path/www" \
    -d "$domains" \
    --keylength ec-256 \
    --force

# =========================================================
# INSTALAR CERTIFICADO
# =========================================================

echo ">>> Instalando certificado..."

"$ACME_BIN" --install-cert \
    -d "$domains" \
    --key-file "$data_path_conf/live/$domains/privkey.pem" \
    --fullchain-file "$data_path_conf/live/$domains/fullchain.pem" \
    --reloadcmd "cd $PROJECT_DIR && docker compose exec -T nginx_vm nginx -s reload"

echo "========================================="
echo " SSL CONFIGURADO CORRECTAMENTE"
echo "========================================="