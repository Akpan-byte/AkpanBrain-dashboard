#!/bin/bash
# AkpanBrain Sync - Bidirectional sync with Google Drive
# Usage: ./sync.sh [push|pull|both]

RCLONE_CONF="/config/.config/rclone/rclone.conf"
BRAIN_DIR="/config/brain"
REMOTE="gdrive:AkpanBrain/brain"
LOG="/config/brain/sync.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

case "${1:-both}" in
    push)
        log "🔄 Pushing to Google Drive..."
        rclone sync "$BRAIN_DIR" "$REMOTE" --config "$RCLONE_CONF" --create-empty-src-dirs -v
        log "✅ Push complete"
        ;;
    pull)
        log "🔄 Pulling from Google Drive..."
        rclone sync "$REMOTE" "$BRAIN_DIR" --config "$RCLONE_CONF" --create-empty-src-dirs -v
        log "✅ Pull complete"
        ;;
    both)
        log "🔄 Bidirectional sync (Drive → Local then Local → Drive)..."
        rclone sync "$REMOTE" "$BRAIN_DIR" --config "$RCLONE_CONF" --create-empty-src-dirs -v
        rclone sync "$BRAIN_DIR" "$REMOTE" --config "$RCLONE_CONF" --create-empty-src-dirs -v
        log "✅ Sync complete"
        ;;
    *)
        echo "Usage: $0 [push|pull|both]"
        exit 1
        ;;
esac

# Verify
log "📊 Verification:"
rclone ls "$REMOTE" --config "$RCLONE_CONF" | while read size file; do
    log "  $file ($size bytes)"
done