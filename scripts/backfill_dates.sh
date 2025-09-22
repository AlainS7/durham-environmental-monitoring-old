#!/usr/bin/env bash
set -euo pipefail
# Backfill a range of dates (inclusive) using Cloud Run job.
# Usage: ./scripts/backfill_dates.sh START_DATE END_DATE
# Dates in YYYY-MM-DD
START=${1:?start date required}
END=${2:?end date required}
JOB_NAME=${JOB_NAME:-weather-data-uploader}
REGION=${REGION:-us-east1}
PROJECT_ID=${PROJECT_ID:-durham-weather-466502}

start_ts=$(date -d "$START" +%s)
end_ts=$(date -d "$END" +%s)
if [ "$end_ts" -lt "$start_ts" ]; then
  echo "[backfill] END < START" >&2; exit 1; fi

cur_ts=$start_ts
while [ "$cur_ts" -le "$end_ts" ]; do
  d=$(date -u -d @${cur_ts} +%F)
  echo "[backfill] Executing job for $d"
  gcloud run jobs execute "$JOB_NAME" --region "$REGION" --project "$PROJECT_ID" --args="--start=$d","--end=$d" --wait
  cur_ts=$((cur_ts + 86400))
  sleep 2
done

echo "[backfill] Complete"
