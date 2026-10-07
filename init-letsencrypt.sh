#!/bin/bash

set -Eeuo pipefail


# =========================================================
# IICA Plataforma
# Let's Encrypt / acme.sh
# =========================================================


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_DIR="$SCRIPT_DIR"

DOMAIN="${1:-}"
EMAIL="${2:-}"


if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then

    echo ""
    echo "Uso:"
    echo "  sudo ./init-letsencrypt.sh dominio correo"
    echo ""

    exit 1

fi


if [[ "$EUID" -ne 0 ]]; then

    echo "ERROR: este script debe ejecutarse con sudo."

    exit 1

fi


ACME_HOME="/root/.acme.sh"

ACME_BIN="$ACME_HOME/acme.sh"

DATA_PATH="$PROJECT_DIR/letsencrypt"

WEBROOT="$DATA_PATH/www"

CERT_DIR="$DATA_PATH/conf/live/$DOMAIN"


echo ""
echo "========================================="
echo " Let's Encrypt"
echo "========================================="
echo "Dominio : $DOMAIN"
echo "Proyecto: $PROJECT_DIR"
echo ""


# =========================================================
# DEPENDENCIAS
# =========================================================

echo ">>> Instalando dependencias..."

apt-get update -qq

apt-get install -y curl cron


systemctl enable cron >/dev/null 2>&1 || true

systemctl start cron >/dev/null 2>&1 || true


# =========================================================
# DIRECTORIOS
# =========================================================

mkdir -p "$WEBROOT"

mkdir -p "$CERT_DIR"


chmod 755 "$DATA_PATH"

chmod 755 "$WEBROOT"


# =========================================================
# VERIFICAR DNS
# =========================================================

echo ">>> Verificando DNS..."

PUBLIC_IP="$(curl -4 -s https://ifconfig.me)"

RESOLVED_IP=""

if command -v getent >/dev/null 2>&1; then

    RESOLVED_IP="$(getent ahostsv4 "$DOMAIN" | awk 'NR==1 {print $1}')"

fi


if [[ -z "$RESOLVED_IP" ]]; then

    echo ""
    echo "ERROR: $DOMAIN no resuelve desde la VM."
    echo ""
    echo "IP pública de la VM:"
    echo "  $PUBLIC_IP"
    echo ""
    echo "Comprueba la delegación DNS antes de continuar."
    echo ""

    exit 1

fi


if [[ "$RESOLVED_IP" != "$PUBLIC_IP" ]]; then

    echo ""
    echo "ERROR: el dominio resuelve a una IP diferente."
    echo ""
    echo "Dominio : $RESOLVED_IP"
    echo "VM      : $PUBLIC_IP"
    echo ""

    exit 1

fi


echo "DNS correcto:"
echo "  $DOMAIN -> $PUBLIC_IP"


# =========================================================
# INSTALAR ACME.SH
# =========================================================

if [[ ! -x "$ACME_BIN" ]]; then

    echo ""
    echo ">>> Instalando acme.sh..."

    curl -fsSL https://get.acme.sh | sh -s email="$EMAIL"

fi


if [[ ! -x "$ACME_BIN" ]]; then

    echo ""
    echo "ERROR: no se pudo instalar acme.sh."

    exit 1

fi


# =========================================================
# CA
# =========================================================

echo ">>> Configurando Let's Encrypt..."

"$ACME_BIN" \
    --set-default-ca \
    --server letsencrypt


# =========================================================
# ACCOUNT
# =========================================================

"$ACME_BIN" \
    --register-account \
    -m "$EMAIL" \
    --server letsencrypt \
    || true


# =========================================================
# CERTIFICADO
# =========================================================

echo ""
echo ">>> Solicitando certificado..."

"$ACME_BIN" \
    --issue \
    --webroot "$WEBROOT" \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    --keylength ec-256


# =========================================================
# INSTALAR CERTIFICADO
# =========================================================

echo ""
echo ">>> Instalando certificado..."

"$ACME_BIN" \
    --install-cert \
    -d "$DOMAIN" \
    --ecc \
    --key-file "$CERT_DIR/privkey.pem" \
    --fullchain-file "$CERT_DIR/fullchain.pem" \
    --reloadcmd "$PROJECT_DIR/ssl-renew.sh"


# =========================================================
# VERIFICAR
# =========================================================

if [[ ! -f "$CERT_DIR/fullchain.pem" ]]; then

    echo ""
    echo "ERROR: no se creó fullchain.pem."

    exit 1

fi


if [[ ! -f "$CERT_DIR/privkey.pem" ]]; then

    echo ""
    echo "ERROR: no se creó privkey.pem."

    exit 1

fi


echo ""
echo "========================================="
echo " SSL CONFIGURADO"
echo "========================================="
echo ""
echo "Certificado:"
echo "  $CERT_DIR/fullchain.pem"
echo ""
echo "Clave:"
echo "  $CERT_DIR/privkey.pem"
echo ""