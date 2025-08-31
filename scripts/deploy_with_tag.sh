#!/usr/bin/env bash
set -euo pipefail
# Deploy (terraform apply) using a specific tag for all three images.
# Usage: ./scripts/deploy_with_tag.sh -p <PROJECT_ID> -b <BUCKET> -t <TAG> [-r region] [-R repo] [--extra "-var foo=bar"]

REGION=us-central1
REPO=weather-maintenance-images
EXTRA_ARGS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--project) PROJECT_ID="$2"; shift 2;;
    -b|--bucket) GCS_BUCKET="$2"; shift 2;;
    -t|--tag) TAG="$2"; shift 2;;
    -r|--region) REGION="$2"; shift 2;;
    -R|--repo) REPO="$2"; shift 2;;
    --extra) EXTRA_ARGS+=" $2"; shift 2;;
    *) echo "Unknown arg $1"; exit 1;;
  esac
done

: "${PROJECT_ID:?project required}"
: "${GCS_BUCKET:?bucket required}"
: "${TAG:?tag required}"

BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"

pushd infra/terraform >/dev/null
terraform init -upgrade
terraform apply \
  -var project_id="${PROJECT_ID}" \
  -var gcs_bucket="${GCS_BUCKET}" \
  -var ingestion_image="${BASE}/ingestion:${TAG}" \
  -var refresh_image="${BASE}/refresh-partitions:${TAG}" \
  -var metrics_image="${BASE}/record-metrics:${TAG}" \
  $EXTRA_ARGS
popd >/dev/null

echo "Deployed with tag ${TAG}. Validate runs, then pin: ./scripts/pin_image_digests.sh ${PROJECT_ID} ${REGION} ${REPO}"
