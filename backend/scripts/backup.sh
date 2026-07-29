#!/bin/bash
# ============================================================
# uroboros — daily backup: PostgreSQL + fotos de perfil
# Runs via cron at 2:00 AM. Retains 30 days of backups.
# Sends Telegram notification on success or failure.
#
# Son dos ficheros con el mismo sello de tiempo, no uno: al restaurar hay que
# acordarse de los dos. Un dump sin las fotos deja filas apuntando a ficheros
# que no existen (la app lo aguanta — cae al avatar de siempre — pero las fotos
# no vuelven).
# ============================================================

set -euo pipefail

BACKUP_DIR="/var/backups/uroboros"
DB_NAME="uroboros"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/uroboros_${DATE}.sql.gz"
MEDIA_FILE="$BACKUP_DIR/uroboros_media_${DATE}.tar.gz"
ENV_FILE="/opt/uroboros/backend/.env"
LOG_TAG="[uroboros-backup]"

# --------------- load env (for Telegram credentials) --------
if [ -f "$ENV_FILE" ]; then
    set -o allexport
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +o allexport
fi

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
# El .env ya se ha cargado arriba, así que MEDIA_DIR viene de ahí; el default
# es el mismo que escribe install.sh.
MEDIA_DIR="${MEDIA_DIR:-/var/lib/uroboros/media}"

# --------------- helpers ------------------------------------
tg_send() {
    local msg="$1"
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
            --data-urlencode "text=${msg}" \
            --data-urlencode "parse_mode=Markdown" \
            > /dev/null || true
    fi
}

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_TAG $*"; }

# --------------- run backup ---------------------------------
log "Iniciando backup → $BACKUP_FILE"
mkdir -p "$BACKUP_DIR"

if sudo -u postgres pg_dump "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)

    # ----- fotos de perfil -----
    # Que falten las fotos no invalida el backup de la BD: se avisa y se sigue.
    MEDIA_SIZE="—"
    if [ -d "$MEDIA_DIR" ]; then
        if tar -czf "$MEDIA_FILE" -C "$(dirname "$MEDIA_DIR")" "$(basename "$MEDIA_DIR")"; then
            MEDIA_SIZE=$(du -sh "$MEDIA_FILE" | cut -f1)
        else
            log "AVISO: el backup de fotos ha fallado"
            rm -f "$MEDIA_FILE"
            MEDIA_SIZE="falló"
        fi
    else
        log "AVISO: no existe $MEDIA_DIR — sin fotos que guardar"
        MEDIA_SIZE="sin directorio"
    fi

    # Remove backups older than RETENTION_DAYS
    find "$BACKUP_DIR" -name "uroboros_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete
    find "$BACKUP_DIR" -name "uroboros_media_*.tar.gz" -mtime "+${RETENTION_DAYS}" -delete

    COUNT=$(find "$BACKUP_DIR" -name "uroboros_*.sql.gz" | wc -l)

    log "Backup completado. BD: $SIZE. Fotos: $MEDIA_SIZE. Backups guardados: $COUNT"

    tg_send "✅ *[uroboros]* Backup completado

*Base de datos:* ${SIZE}
*Fotos de perfil:* ${MEDIA_SIZE}
*Backups guardados:* ${COUNT} (últimos ${RETENTION_DAYS} días)
*Archivo:* \`uroboros_${DATE}.sql.gz\`"

else
    log "ERROR: el backup ha fallado"
    rm -f "$BACKUP_FILE"

    tg_send "🔴 *[uroboros]* BACKUP FALLIDO

El backup nocturno de PostgreSQL ha fallado.
Revisa: \`journalctl -u cron\` o \`/var/log/uroboros-backup.log\`"

    exit 1
fi
