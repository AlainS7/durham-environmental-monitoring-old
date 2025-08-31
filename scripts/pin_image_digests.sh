#!/usr/bin/env bash
set -euo pipefail

# Fetch latest digests for ingestion, refresh, metrics images and output terraform apply command.
# Usage: ./scripts/pin_image_digests.sh <PROJECT_ID> [REGION] [REPO]
PROJECT_ID=${1:?"PROJECT_ID required"}
REGION=${2:-us-central1}
REPO=${3:-weather-maintenance-images}

function latest_digest() {
  local image=$1
  gcloud artifacts docker images list ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${image} \
    --format='value(DIGEST)' \
    --sort-by=~CREATE_TIME | head -n1
}

INGEST_DIGEST=$(latest_digest ingestion || true)
REFRESH_DIGEST=$(latest_digest refresh-partitions || true)
METRICS_DIGEST=$(latest_digest record-metrics || true)

if [[ -z "$INGEST_DIGEST" || -z "$REFRESH_DIGEST" || -z "$METRICS_DIGEST" ]]; then
  echo "One or more digests missing. Ensure images are built (cloudbuild.multi.yaml)." >&2
  exit 1
fi

echo "# Apply with pinned digests:" >&2
echo "terraform apply \"-var=ingestion_image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/ingestion@${INGEST_DIGEST}\" \\
  \"-var=refresh_image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/refresh-partitions@${REFRESH_DIGEST}\" \\
  \"-var=metrics_image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/record-metrics@${METRICS_DIGEST}\"" 