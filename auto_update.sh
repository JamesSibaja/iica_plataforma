#!/bin/bash

set -e

# =========================================================
# IICA Plataforma - Actualización automática
# =========================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$PROJECT_DIR/auto_update.log"

# ---------------------------------------------------------
# FUNCIONES
# ---------------------------------------------------------

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ---------------------------------------------------------
# IR AL DIRECTORIO DEL PROYECTO
# ---------------------------------------------------------

cd "$PROJECT_DIR" || {
    log "ERROR: No se pudo acceder a $PROJECT_DIR"
    exit 1
}

log "========================================="
log " INICIO DE ACTUALIZACIÓN AUTOMÁTICA"
log "========================================="

# ---------------------------------------------------------
# COMPROBAR GIT
# ---------------------------------------------------------

if [ ! -d ".git" ]; then
    log "ERROR: $PROJECT_DIR no parece ser un repositorio Git"
    exit 1
fi

# ---------------------------------------------------------
# OBTENER CAMBIOS DEL REPOSITORIO
# ---------------------------------------------------------

log "Consultando GitHub..."

git fetch origin main

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

log "Commit local : $LOCAL"
log "Commit remoto: $REMOTE"

# ---------------------------------------------------------
# COMPARAR VERSIONES
# ---------------------------------------------------------

if [ "$LOCAL" = "$REMOTE" ]; then

    log "No hay cambios nuevos en GitHub."
    log "No es necesario realizar un deploy."

else

    log "Se detectaron cambios en GitHub."
    log "Iniciando deploy..."

    # -----------------------------------------------------
    # DEPLOY
    # -----------------------------------------------------

    make deploy

    log "Deploy completado correctamente."

fi

log "========================================="
log " FIN DE ACTUALIZACIÓN AUTOMÁTICA"
log "========================================="