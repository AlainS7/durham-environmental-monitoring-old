#!/usr/bin/env bash
set -euo pipefail

JOB_NAME=${JOB_NAME:-weather-data-uploader}
REGION=${REGION:-us-east1}
PROJECT_ID=${PROJECT_ID:-durham-weather-466502}
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

  log "Status: ${STATUS:-unknown} ${LASTMSG} (t=${elapsed}s)"
  if [ "$STATUS" = "True" ]; then
    # Check success vs failure count
    FAILED=$(echo "$EXECUTION_JSON" | jq -r '.failedCount // 0')
    if [ "${FAILED:-0}" -gt 0 ]; then
      err "Execution completed with failed tasks (failedCount=$FAILED)."; exit 2
    fi
    log "Execution succeeded."; break
  fi
  if [ "$STATUS" = "False" ]; then
    err "Execution ended in failure state: $LASTMSG"; exit 3
  fi
  if [ $elapsed -ge $MAX_WAIT ]; then
    err "Timed out waiting for completion ($MAX_WAIT s)."; exit 4
  fi
  sleep $POLL_DELAY
  elapsed=$((elapsed+POLL_DELAY))
done

log "Fetching last 200 log lines (if available)"
gcloud logging read "resource.type=cloud_run_job AND resource.labels.execution_name=$EXEC_ID" --project "$PROJECT_ID" --limit=200 --format="value(textPayload)" 2>/dev/null || log "No logs retrieved"

log "Done."
