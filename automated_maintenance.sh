#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs temp
LOG_FILE="logs/maintenance_$(date '+%Y%m%d_%H%M%S').log"
{
  echo "[$(date -Is)] Starting maintenance"
  echo "Cleaning temp directory..."
  find temp -type f -mtime +7 -print -delete || true
  echo "[$(date -Is)] Maintenance complete"
} | tee "$LOG_FILE"
exit 0
