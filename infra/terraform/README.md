# Terraform Infrastructure Skeleton

This module provisions core infra for the Durham Environmental Monitoring pipeline.

## Resources

* GCS bucket (raw Parquet). By default no lifecycle deletion (infinite retention). Optional lifecycle can be enabled by setting `raw_retention_days` > 0 (set to 0 or remove rule for infinite retention).
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
  raw_retention_days  = 0 # infinite retention

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

Create a trigger pointing at `cloudbuild.multi.yaml` with substitutions `_REGION` and `_REPO` if you diverge from defaults:

```yaml
# cloudbuild.multi.yaml (already in repo root)
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build','-t','${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/ingestion:${SHORT_SHA}','-t','${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/ingestion:latest','--build-arg','APP_SCRIPT=src/data_collection/daily_data_collector.py','.' ]
  # ... other steps omitted (refresh, metrics)
```

After a successful build, optionally update Terraform vars to freeze versions:

```bash
export IMG_SHA=$(gcloud artifacts docker images list ${REGION}-docker.pkg.dev/$PROJECT_ID/${REPO} --format='value(DIGEST)' --filter='ingestion' | head -n1)
# Update ingestion_image to include @sha256: digest.
```
