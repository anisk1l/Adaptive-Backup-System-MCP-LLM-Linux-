#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$PROJECT_DIR/tuner_decisions.log"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') Adaptive run ===" | tee -a "$LOG"

# 1) Decide based on Netdata
if python3 "$PROJECT_DIR/tuner.py" | tee -a "$LOG"; then
  echo "[OK] Tuner says SAFE → running backup" | tee -a "$LOG"
else
  echo "[SKIP] Tuner says UNSAFE → skipping backup" | tee -a "$LOG"
  exit 0
fi

# 2) Run your existing backup script (still does its own checks & logs)
bash "$PROJECT_DIR/easy_backup.sh" | tee -a "$LOG"
