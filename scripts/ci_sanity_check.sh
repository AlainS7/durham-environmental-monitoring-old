#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=${PROJECT_ID:-durham-weather-466502}
DATASET="sensors"
SECRET_ID="prod-db-credentials"
BUCKET="sensor-data-to-bigquery"

log() { echo "[sanity] $*"; }
warn() { echo "[sanity][warn] $*"; }

log "Active account:" || true
gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || warn "Could not list active account"

log "List bucket top-level paths (non-fatal)"
gcloud storage ls "gs://${BUCKET}" 2>/dev/null || warn "No access to bucket or bucket missing: ${BUCKET}"

log "Secret metadata (optional)"
if gcloud secrets describe "${SECRET_ID}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud secrets versions list "${SECRET_ID}" --project="${PROJECT_ID}" --limit=3 2>/dev/null || warn "Cannot list secret versions"
else
  warn "Secret ${SECRET_ID} not visible (expected if least-privileged)"
fi

log "BigQuery dataset metadata (optional)"
if bq --project_id="${PROJECT_ID}" show "${PROJECT_ID}:${DATASET}" >/dev/null 2>&1; then
  bq --project_id="${PROJECT_ID}" ls --max_results=20 "${PROJECT_ID}:${DATASET}" 2>/dev/null || warn "Cannot list tables (need metadataViewer)"
else
  warn "Dataset ${PROJECT_ID}:${DATASET} not visible"
fi

log "Sanity checks complete (no failures block build)."
