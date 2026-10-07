#!/bin/bash

set -Eeuo pipefail


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"


cd "$SCRIPT_DIR"


echo ">>> Recargando Nginx..."


if docker compose ps --status running nginx_vm >/dev/null 2>&1; then

    docker compose exec -T nginx_vm nginx -t

    docker compose exec -T nginx_vm nginx -s reload

    echo ">>> Nginx recargado correctamente."

else

    echo ">>> Nginx no está ejecutándose."

fi