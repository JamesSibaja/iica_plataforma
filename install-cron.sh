#!/bin/bash

set -e

PROJECT_DIR="/home/usuario/iica_plataforma"

CRON_JOB="0 6 * * * $PROJECT_DIR/auto_update.sh >> $PROJECT_DIR/auto_update.log 2>&1"

echo ">>> Configurando actualización automática diaria..."

CURRENT_CRONTAB=$(crontab -l 2>/dev/null || true)

if echo "$CURRENT_CRONTAB" | grep -Fq "$PROJECT_DIR/auto_update.sh"; then

    echo ">>> El cron de actualización ya existe."

else

    (
        echo "$CURRENT_CRONTAB"
        echo "$CRON_JOB"
    ) | crontab -

    echo ">>> Cron configurado correctamente."

fi