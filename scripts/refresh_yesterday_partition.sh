#!/usr/bin/env bash
set -euo pipefail
# Refresh yesterday's partition for materialized tables from external sources.
# Usage: ./scripts/refresh_yesterday_partition.sh [PROJECT_ID] [DATASET]
PROJECT_ID=${1:-${BQ_PROJECT:-durham-weather-466502}}
DATASET=${2:-${BQ_DATASET:-sensors}}
YESTERDAY=$(date -u -d 'yesterday' +%F)

echo "[refresh] Project=$PROJECT_ID Dataset=$DATASET Date=$YESTERDAY"

bq query --project_id "$PROJECT_ID" --use_legacy_sql=false "DELETE FROM \`${PROJECT_ID}.${DATASET}.wu_raw_materialized\` WHERE DATE(timestamp)='${YESTERDAY}'" || true
bq query --project_id "$PROJECT_ID" --use_legacy_sql=false "INSERT INTO \`${PROJECT_ID}.${DATASET}.wu_raw_materialized\` SELECT * FROM \`${PROJECT_ID}.${DATASET}.wu_raw_external\` WHERE DATE(timestamp)='${YESTERDAY}'" || true

bq query --project_id "$PROJECT_ID" --use_legacy_sql=false "DELETE FROM \`${PROJECT_ID}.${DATASET}.tsi_raw_materialized\` WHERE DATE(timestamp)='${YESTERDAY}'" || true
bq query --project_id "$PROJECT_ID" --use_legacy_sql=false "INSERT INTO \`${PROJECT_ID}.${DATASET}.tsi_raw_materialized\` SELECT * FROM \`${PROJECT_ID}.${DATASET}.tsi_raw_external\` WHERE DATE(timestamp)='${YESTERDAY}'" || true

echo "[refresh] Done"
