# Terraform Infrastructure Skeleton

This module provisions core infra for the Durham Environmental Monitoring pipeline.

## Resources

* GCS bucket (raw Parquet). Infinite retention by default (no lifecycle rule). Enable time-based deletion by setting `raw_retention_days` > 0.
* BigQuery dataset for raw & transformed tables.
* Ingestion & verifier service accounts with least privilege example roles.
* Cloud Run Jobs: ingestion, partition refresh, metrics recording.
* Cloud Scheduler jobs invoking each Cloud Run job via OIDC.

## Usage

```hcl
module "sensor_pipeline" {
  source              = "./infra/terraform"
  project_id          = var.project_id
  region              = var.region
  gcs_bucket          = "my-sensor-raw-bucket"
  bq_dataset          = "sensors"
  gcs_prefix          = "sensor_readings"
  raw_retention_days  = 0 # infinite retention (no lifecycle block rendered)

  # Images (built separately by Cloud Build multi-image pipeline)
  ingestion_image     = "us-central1-docker.pkg.dev/${var.project_id}/weather-maintenance-images/ingestion:latest"
  refresh_image       = "us-central1-docker.pkg.dev/${var.project_id}/weather-maintenance-images/refresh-partitions:latest"
  metrics_image       = "us-central1-docker.pkg.dev/${var.project_id}/weather-maintenance-images/record-metrics:latest"

  # Schedules (UTC cron)
  ingestion_cron      = "5 7 * * *"   # 07:05 UTC daily ingestion
  refresh_cron        = "0 4 * * *"   # 04:00 UTC partition refresh
  metrics_cron        = "10 4 * * *"  # 04:10 UTC metrics capture
}
```

Then:

```bash
terraform init
terraform plan -var project_id=YOUR_PROJECT -var gcs_bucket=your-bucket-name
terraform apply -var project_id=YOUR_PROJECT -var gcs_bucket=your-bucket-name
```

## Next Steps

* Add Workload Identity Federation provider & IAM binding conditions.
* Split roles into custom minimal roles if needed.
* Add Cloud Scheduler + Cloud Run job resources for end-to-end automation.
* Optionally pin images to immutable SHAs/digests instead of :latest (update *_image vars after Cloud Build).

## Cloud Build (multi-image) Example

Create a trigger pointing at `cloudbuild.multi.yaml` with substitutions `_REGION`, `_REPO`, and `_TAG` (choose a tag strategy: date, commit, etc.).

Excerpt (simplified) from `cloudbuild.multi.yaml` now using `_TAG` substitution:

```yaml
steps:
  - id: Build ingestion image
    name: gcr.io/cloud-builders/docker
    args: ["build","-t","${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/ingestion:${_TAG}","-t","${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/ingestion:latest","--build-arg","APP_SCRIPT=src/data_collection/daily_data_collector.py","."]
  # ... refresh & metrics steps similar
substitutions:
  _REGION: us-central1
  _REPO: weather-maintenance-images
  _TAG: manual
```

Trigger example (manual tag injection):

```bash
gcloud builds submit --config=cloudbuild.multi.yaml --substitutions=_TAG=$(date +%Y%m%d%H%M)
```

After a successful build, optionally update Terraform vars to freeze versions (swap `:latest` for `:<tag>` or digests):

```bash
./scripts/pin_image_digests.sh "$PROJECT_ID" us-central1 weather-maintenance-images
"# Copy the terraform apply command above to pin all three images" 
```

## Artifact Registry Creation

Option A (Terraform): set `create_artifact_repo=true` and supply `artifact_repo` (defaults to weather-maintenance-images).

Option B (gcloud manual):
 
```bash
gcloud artifacts repositories create weather-maintenance-images \
  --repository-format=DOCKER --location=us-central1 \
  --description="Sensor ingestion + maintenance images"
```

## One-Shot Bootstrap Script

To provision everything (optional repo creation, build images, apply Terraform, optional digest pin):

```bash
./scripts/bootstrap_infra.sh \
  --project YOUR_PROJECT_ID \
  --bucket YOUR_GCS_BUCKET \
  --create-repo \
  --pin
```

Flags:

* `--create-repo` ensures Artifact Registry exists (skip if pre-created)
* `--pin` prints a terraform command with image digests to lock versions


