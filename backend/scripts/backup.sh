#!/bin/bash
# ============================================================
# uroboros — PostgreSQL daily backup
# Runs via cron at 2:00 AM. Retains 30 days of backups.
# Sends Telegram notification on success or failure.
# ============================================================

set -euo pipefail

BACKUP_DIR="/var/backups/uroboros"
DB_NAME="uroboros"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/uroboros_${DATE}.sql.gz"
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

    # Remove backups older than RETENTION_DAYS
    find "$BACKUP_DIR" -name "uroboros_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

    COUNT=$(find "$BACKUP_DIR" -name "uroboros_*.sql.gz" | wc -l)

    log "Backup completado. Tamaño: $SIZE. Backups guardados: $COUNT"

    tg_send "✅ *[uroboros]* Backup completado

*Tamaño:* ${SIZE}
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
