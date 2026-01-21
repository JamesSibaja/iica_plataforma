#!/bin/bash
set -e

domains=$1
email=$2

ACME_HOME="/opt/acme.sh"
ACME_BIN="$ACME_HOME/acme.sh"

data_path="./letsencrypt"
data_path_conf="./letsencrypt/conf"

# -------------------------
# ROOT CHECK
# -------------------------
if [[ "$EUID" -ne 0 ]]; then
  echo "❌ Ejecuta este script con sudo"
  exit 1
fi

if [[ -z "$domains" || -z "$email" ]]; then
  echo "Uso: sudo ./init-letsencrypt.sh dominio correo"
  exit 1
fi

# -------------------------
# DEPENDENCIAS
# -------------------------
echo ">>> Verificando dependencias..."
apt-get update -qq
apt-get install -y curl cron

# -------------------------
# DIRECTORIOS
# -------------------------
mkdir -p "$data_path/www"
mkdir -p "$data_path_conf/live/$domains"

# -------------------------
# INSTALAR ACME.SH
# -------------------------
if [[ ! -f "$ACME_BIN" ]]; then
  echo ">>> Instalando acme.sh en $ACME_HOME"
  mkdir -p "$ACME_HOME"
  curl https://get.acme.sh | sh -s email="$email" home="$ACME_HOME"
fi

# -------------------------
# CONFIGURAR ACME.SH
# -------------------------
"$ACME_BIN" --set-default-ca --server zerossl
"$ACME_BIN" --register-account -m "$email" --server zerossl || true

# -------------------------
# OBTENER CERTIFICADOS
# -------------------------
echo ">>> Solicitando certificados para $domains"

"$ACME_BIN" --issue \
  --webroot "$data_path/www" \
  -d "$domains" \
  --keylength ec-256 \
  --force

# -------------------------
# INSTALAR CERTIFICADOS
# -------------------------
echo ">>> Instalando certificados..."

"$ACME_BIN" --install-cert -d "$domains" \
  --key-file "$data_path_conf/live/$domains/privkey.pem" \
  --fullchain-file "$data_path_conf/live/$domains/fullchain.pem" \
  --reloadcmd "docker compose exec nginx_vm nginx -s reload"

echo "✅ Certificados SSL instalados correctamente"
