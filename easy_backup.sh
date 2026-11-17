#!/usr/bin/env bash

MAX_LOAD=2
MIN_FREE=20
LOGFILE="/var/log/adaptive_backup.log"
SOURCE="/mnt/c/Users/mdwas/Documents"     # Folder you want to backup
TARGET="/mnt/c/Users/mdwas/Backup"        # Backup destination

mkdir -p "$TARGET"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

log "=== Adaptive Backup Started ==="

LOAD=$(cut -d " " -f1 /proc/loadavg)
LOAD_INT=${LOAD%.*}
FREE=$((100 - $(df -P / | awk 'NR==2{gsub("%","",$5);print $5}')))

# Conditions
if [ "$LOAD_INT" -ge "$MAX_LOAD" ]; then
    log "❌ Load too high ($LOAD). Skipping."
    exit 1
fi

if [ "$FREE" -lt "$MIN_FREE" ]; then
    log "❌ Low disk space ($FREE%). Skipping."
    exit 1
fi

log "System OK — running backup..."

BACKUP_NAME="backup_$(date '+%Y-%m-%d_%H-%M-%S').tar.gz"
tar -czf "$TARGET/$BACKUP_NAME" "$SOURCE"

log "🎉 Backup completed: $TARGET/$BACKUP_NAME"
exit 0
