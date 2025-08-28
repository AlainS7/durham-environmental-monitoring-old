#!/usr/bin/env bash
set -euo pipefail

# Require jq for JSON parsing (GitHub Actions runners include it by default)
if ! command -v jq >/dev/null 2>&1; then
  echo "[run-job][error] jq is required but not installed. Install jq and retry." >&2
  exit 10
fi

JOB_NAME=${JOB_NAME:-weather-data-uploader}
REGION=${REGION:-us-east1}
: "${PROJECT_ID:?PROJECT_ID environment variable must be set}"
POLL_DELAY=5
MAX_WAIT=${MAX_WAIT:-600}

log(){ echo "[run-job] $*"; }
err(){ echo "[run-job][error] $*" >&2; }

log "Executing Cloud Run job: $JOB_NAME in $REGION (project: $PROJECT_ID)"
EXEC_ID=$(gcloud run jobs execute "$JOB_NAME" --region "$REGION" --project "$PROJECT_ID" --format="value(metadata.name)" 2>/dev/null || true)
if [ -z "$EXEC_ID" ]; then
  err "Failed to start execution (check IAM or job existence)."; exit 1
fi
log "Started execution: $EXEC_ID"

elapsed=0
while true; do
  EXECUTION_JSON=$(gcloud run jobs executions describe "$EXEC_ID" --region "$REGION" --project "$PROJECT_ID" --format="json" 2>/dev/null || echo "{}")
  STATUS=$(echo "$EXECUTION_JSON" | jq -r '(.status.conditions[]? | select(.type=="Completed") | .state) // empty')
  LASTMSG=$(echo "$EXECUTION_JSON" | jq -r '(.status.conditions[]? | select(.type=="Completed") | .message) // empty')
  FAILED_COUNT=$(echo "$EXECUTION_JSON" | jq -r '.failedCount // 0')
  SUCCEEDED_COUNT=$(echo "$EXECUTION_JSON" | jq -r '.succeededCount // 0')
  ACTIVE_COUNT=$(echo "$EXECUTION_JSON" | jq -r '.runningCount // 0')

  log "Status: ${STATUS:-unknown} ${LASTMSG} (t=${elapsed}s) failed=${FAILED_COUNT} succeeded=${SUCCEEDED_COUNT} running=${ACTIVE_COUNT}"
  # Early exit if tasks have failed and no tasks are running anymore but controller hasn't set Completed=False yet
  if [ "$FAILED_COUNT" -gt 0 ] && [ "$ACTIVE_COUNT" -eq 0 ] && [ "${STATUS:-}" != "True" ]; then
    err "Detected failed tasks before controller marked completion (failedCount=$FAILED_COUNT).";
    if [ "${DEBUG_EXECUTION_JSON:-}" = "1" ]; then
      echo "$EXECUTION_JSON" | jq '.' >&2 || true
    fi
    break
  fi
  if [ "$STATUS" = "True" ]; then
    # Check success vs failure count
    FAILED=$(echo "$EXECUTION_JSON" | jq -r '.failedCount // 0')
    if [ "${FAILED:-0}" -gt 0 ]; then
      err "Execution completed with failed tasks (failedCount=$FAILED).";
      if [ "${DEBUG_EXECUTION_JSON:-}" = "1" ]; then
        echo "$EXECUTION_JSON" | jq '.' >&2 || true
      fi
      exit 2
    fi
    log "Execution succeeded."; break
  fi
  if [ "$STATUS" = "False" ]; then
    err "Execution ended in failure state: $LASTMSG";
    if [ "${DEBUG_EXECUTION_JSON:-}" = "1" ]; then
      echo "$EXECUTION_JSON" | jq '.' >&2 || true
    fi
    exit 3
  fi
  if [ $elapsed -ge $MAX_WAIT ]; then
    err "Timed out waiting for completion ($MAX_WAIT s).";
    if [ "${DEBUG_EXECUTION_JSON:-}" = "1" ]; then
      echo "$EXECUTION_JSON" | jq '.' >&2 || true
    fi
    exit 4
  fi
  sleep $POLL_DELAY
  elapsed=$((elapsed+POLL_DELAY))
done

log "Fetching last 200 log lines (if available)"
gcloud logging read "resource.type=cloud_run_job AND resource.labels.execution_name=$EXEC_ID" --project "$PROJECT_ID" --limit=200 --format="value(textPayload)" 2>/dev/null || log "No logs retrieved"

log "Done."
