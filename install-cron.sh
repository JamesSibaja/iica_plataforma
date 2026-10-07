#!/bin/bash

set -Eeuo pipefail


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_USER="$(stat -c '%U' "$SCRIPT_DIR")"


CRON_FILE="/etc/cron.d/iica-plataforma"


cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

CRON_TZ=America/Costa_Rica

0 3 * * * $PROJECT_USER cd $SCRIPT_DIR && $SCRIPT_DIR/auto_update.sh >> $SCRIPT_DIR/auto_update.log 2>&1
EOF


chmod 644 "$CRON_FILE"


echo ""
echo "Cron instalado:"
echo ""
cat "$CRON_FILE"
echo ""