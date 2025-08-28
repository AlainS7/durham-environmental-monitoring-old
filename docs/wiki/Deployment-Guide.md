# Deployment Guide

This guide provides instructions for deploying the Hot Durham Environmental Monitoring System. It covers infrastructure setup, application configuration, and deployment processes.

## 🚀 Deployment Overview

The deployment includes:

* Backend API services
* Data ingestion pipelines
* BigQuery datasets and tables
* Scheduled jobs and monitoring
* Optional dashboard components

## 📦 Prerequisites

Before deploying, ensure you have:

* Google Cloud Project with billing enabled
* BigQuery and Cloud Storage APIs activated
* Service account with appropriate permissions
* Terraform installed (for infrastructure as code)
* Python 3.11 environment
* Access to secrets and configuration files

## 🏗️ Infrastructure Provisioning (Terraform)

Infrastructure is managed with Terraform located in `infra/terraform/`.

### 1. Initialize Terraform

```bash
cd infra/terraform
terraform init
```

### 2. Review and Customize Variables

Edit `variables.tf` or create a `terraform.tfvars` file to set:

* `project_id`
* `region`
* `dataset_name`
* `gcs_bucket_name`
* `environment` (e.g., `production`, `development`)

### 3. Validate and Plan

```bash
terraform validate
terraform plan -out=tfplan
```

### 4. Apply Infrastructure Changes

```bash
terraform apply tfplan
```

## 🗄️ Database / BigQuery Setup

BigQuery schemas are defined in `database/schema.sql`.

### 1. Create Dataset (if not managed by Terraform)

```bash
bq --location=US mk -d hot_durham_dataset
```

### 2. Apply Schema

```bash
bq query --use_legacy_sql=false < database/schema.sql
```

### 3. Validate Tables

```bash
bq ls hot_durham_dataset
```

## 🔐 Secrets & Configuration

Configuration files are stored under `config/`.

### 1. Service Account Keys

Store service account JSON securely and set environment variables:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### 2. Environment Configuration

Select environment via configuration modules:

```python
from config.environments import development, production
```

### 3. Sensitive Values

* Store in Secret Manager where possible
* Avoid committing secrets to version control
* Rotate keys regularly

## 🧪 Pre-Deployment Checks

Run verification scripts before deploying to production:

```bash
python scripts/verify_cloud_pipeline.py
python scripts/check_metric_coverage.py
python scripts/check_row_thresholds.py
```

## 📥 Data Ingestion Deployment

Data ingestion scripts pull raw sensor data and load it into BigQuery.

### 1. Fetch Sample Raw Data

```bash
python scripts/fetch_sample_raw.py --sensor all --limit 100
```

### 2. Upload Sample to BigQuery

```bash
python scripts/bq_upload_sample.py --date 2025-08-20
```

### 3. Merge Sensor Readings

```bash
python scripts/merge_sensor_readings.py --start 2025-08-19 --end 2025-08-20
```

## 🔄 Transformations (dbt)

Run dbt transformations after raw data is loaded.

### 1. Install Dependencies

```bash
uv pip sync requirements.txt
uv pip sync requirements-dbt.txt
```

### 2. Compile Models

```bash
dbt compile --profiles-dir .
```

### 3. Run and Test

```bash
dbt run --profiles-dir .
dbt test --profiles-dir .
```

## 🧹 Idempotent Reload / Partition Replace

To reload a single partition/day:

```bash
python scripts/load_to_bigquery.py --replace-date 2025-08-20
```

## 🔁 Incremental MERGE Upserts

Incrementally upsert latest data:

```bash
python scripts/load_to_bigquery.py --incremental --days 1
```

## 📊 Monitoring & Alerts

Monitoring scripts help validate data quality.

```bash
python scripts/verify_db_data.py
python scripts/compare_metrics.py
python scripts/notify_teams.py --channel ops
```

## 🛠️ Maintenance Jobs

Scheduled maintenance tasks:

* Data transformation runs (dbt)
* Data quality checks
* Metric coverage reports
* Alert notifications
* Partition reprocessing

## 🧪 Health Checks

Example health check function for services:

```python
import requests

def check_health(url: str, timeout: float = 3.0) -> bool:
    """Return True if service at url responds with 200 OK within timeout."""
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False
```

Run:

```bash
python -c "from health import check_health; print(check_health('https://example.com/health'))"
```

## 🔍 Troubleshooting

Common issues and fixes:

### 1. Authentication Errors

```bash
# Ensure GOOGLE_APPLICATION_CREDENTIALS is set
echo $GOOGLE_APPLICATION_CREDENTIALS
# Activate service account
gcloud auth activate-service-account --key-file $GOOGLE_APPLICATION_CREDENTIALS
```

### 2. Permission Denied (BigQuery)

```bash
# Check IAM roles
gcloud projects get-iam-policy $PROJECT_ID | grep SERVICE_ACCOUNT_EMAIL
```

### 3. Missing Tables

```bash
bq ls hot_durham_dataset
# Re-apply schema if missing
bq query --use_legacy_sql=false < database/schema.sql
```

### 4. dbt Profile Issues

```bash
# Validate dbt profile
dbt debug --profiles-dir .
```

### 5. Network/Timeout Issues

```bash
# Test connectivity
ping -c 3 api.example.com || true
# Retry with backoff (example snippet)
python - <<'PY'
import time, requests
for attempt in range(3):
    try:
        r = requests.get('https://api.example.com/health', timeout=5)
        print('OK', r.status_code); break
    except Exception as e:
        print('Attempt', attempt+1, 'failed:', e); time.sleep(2**attempt)
else:
    raise SystemExit('Service unreachable')
PY
```

## 📦 Deployment Automation (Optional)

Consider adding CI/CD steps:

* Automated tests on push
* dbt run/test workflows
* Scheduled ingestion jobs
* Lint & style checks

## 🧾 Post-Deployment Verification

Run these checks after deployment:

```bash
python scripts/verify_cloud_pipeline.py
python scripts/compare_metrics.py
python scripts/notify_teams.py --channel ops --summary
```

## 🗂️ Rollback Strategy

If deployment causes issues:

* Revert to previous Git commit
* Re-run stable ingestion & dbt transformations
* Restore backup tables / partitions
* Document root cause and mitigation

## 🔐 Security Hardening (Summary)

* Principle of least privilege for service accounts
* Rotate credentials and keys
* Enable audit logging
* Restrict network access where possible
* Keep dependencies updated

## 📅 Scheduled Jobs

Maintain a schedule for:

* Hourly ingestion (if near-real-time)
* Daily transformations
* Weekly metric audits
* Monthly dependency updates

---

Deployment complete. Monitor logs and metrics to ensure ongoing system health.

Last updated: June 15, 2025
