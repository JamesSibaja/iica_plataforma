#!/bin/bash
set -e

domains=$1
email=$2

ACME_HOME="/root/.acme.sh"
ACME_BIN="$ACME_HOME/acme.sh"

data_path="./letsencrypt"
data_path_conf="./letsencrypt/conf"

# -------------------------
# ROOT CHECK
# -------------------------
if [[ "$EUID" -ne 0 ]]; then
  echo "Ejecuta con sudo"
  exit 1
fi

# -------------------------
# DEPENDENCIAS
# -------------------------
apt-get update -qq
apt-get install -y curl cron

systemctl enable cron || true
systemctl start cron || true

# -------------------------
# DIRECTORIOS
# -------------------------
mkdir -p "$data_path/www"
mkdir -p "$data_path_conf/live/$domains"

# -------------------------
# INSTALAR ACME.SH
# -------------------------
if [[ ! -f "$ACME_BIN" ]]; then
  echo ">>> Instalando acme.sh"
  curl https://get.acme.sh | sh
fi

# -------------------------
# CONFIGURAR ACME.SH
# -------------------------
"$ACME_BIN" --set-default-ca --server zerossl
"$ACME_BIN" --register-account -m "$email" --server zerossl || true

# -------------------------
# EMITIR CERTIFICADO
# -------------------------
"$ACME_BIN" --issue \
  --webroot "$data_path/www" \
  -d "$domains" \
  --keylength ec-256 \
  --force

# -------------------------
# INSTALAR CERTIFICADO
# -------------------------
"$ACME_BIN" --install-cert -d "$domains" \
  --key-file "$data_path_conf/live/$domains/privkey.pem" \
  --fullchain-file "$data_path_conf/live/$domains/fullchain.pem" \
  --reloadcmd "docker compose restart nginx_vm"

echo "SSL configurado correctamente"