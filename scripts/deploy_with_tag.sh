#!/usr/bin/env bash
set -euo pipefail
# Deploy (terraform apply) using a specific tag for all three images.
# Usage: ./scripts/deploy_with_tag.sh -p <PROJECT_ID> -b <BUCKET> -t <TAG> \
#        [-r region] [-R repo] [--no-alerts] [--extra "-var foo=bar"]
# --no-alerts (or --skip-alerts) sets -var=create_alert_policies=false (and leaves notification_channel_ids empty)

REGION=us-central1
REPO=weather-maintenance-images
EXTRA_ARGS=""
SKIP_ALERTS=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--project) PROJECT_ID="$2"; shift 2;;
    -b|--bucket) GCS_BUCKET="$2"; shift 2;;
    -t|--tag) TAG="$2"; shift 2;;
    -r|--region) REGION="$2"; shift 2;;
    -R|--repo) REPO="$2"; shift 2;;
  --no-alerts|--skip-alerts) SKIP_ALERTS=true; shift 1;;
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
  $( $SKIP_ALERTS && echo -var=create_alert_policies=false ) \
  $EXTRA_ARGS
popd >/dev/null

if $SKIP_ALERTS; then
  echo "Deployed (alerts skipped). Later enable with: terraform apply -var=create_alert_policies=true ..."
else
  echo "Deployed with tag ${TAG}."
fi
echo "Validate runs, then pin: ./scripts/pin_image_digests.sh ${PROJECT_ID} ${REGION} ${REPO}"
