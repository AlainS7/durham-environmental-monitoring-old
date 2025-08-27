# Terraform Infrastructure Skeleton

This module provisions core infra for the Durham Environmental Monitoring pipeline.

## Resources
- GCS bucket (raw Parquet) with lifecycle deletion after `raw_retention_days` days.
- BigQuery dataset for raw & transformed tables.
- Ingestion & verifier service accounts with least privilege example roles.

## Usage
```hcl
module "sensor_pipeline" {
  source              = "./infra/terraform"
  project_id          = var.project_id
  region              = var.region
  gcs_bucket          = "my-sensor-raw-bucket"
  bq_dataset          = "sensors"
  raw_retention_days  = 120
}
```

Then:
```bash
terraform init
terraform plan -var project_id=YOUR_PROJECT -var gcs_bucket=your-bucket-name
terraform apply -var project_id=YOUR_PROJECT -var gcs_bucket=your-bucket-name
```

## Next Steps
- Add Workload Identity Federation provider & IAM binding conditions.
- Split roles into custom minimal roles if needed.
- Add Cloud Scheduler + Cloud Run job resources for end-to-end automation.
