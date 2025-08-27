terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# GCS bucket for raw sensor parquet
resource "google_storage_bucket" "raw_bucket" {
  name          = var.gcs_bucket
  location      = var.region
  force_destroy = false
  uniform_bucket_level_access = true
  lifecycle_rule {
    action { type = "Delete" }
    condition { age = var.raw_retention_days }
  }
}

# BigQuery dataset for sensor tables
resource "google_bigquery_dataset" "sensors" {
  dataset_id  = var.bq_dataset
  location    = var.region
  description = "Environmental sensor raw and transformed data"
  delete_contents_on_destroy = false
}

# Service accounts
resource "google_service_account" "ingestion" {
  account_id   = "sensor-ingestion"
  display_name = "Sensor Ingestion"
}

resource "google_service_account" "verifier" {
  account_id   = "sensor-verifier"
  display_name = "Pipeline Verifier"
}

# IAM bindings (least privilege coarse example)
resource "google_project_iam_member" "ingestion_bq_jobuser" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "verifier_bq_jobuser" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.verifier.email}"
}

resource "google_bigquery_dataset_iam_member" "ingestion_dataset_editor" {
  dataset_id = google_bigquery_dataset.sensors.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_bigquery_dataset_iam_member" "verifier_dataset_viewer" {
  dataset_id = google_bigquery_dataset.sensors.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.verifier.email}"
}

resource "google_storage_bucket_iam_member" "ingestion_bucket_writer" {
  bucket = google_storage_bucket.raw_bucket.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_storage_bucket_iam_member" "verifier_bucket_viewer" {
  bucket = google_storage_bucket.raw_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.verifier.email}"
}

# Cloud Run Job for ingestion (container image assumed built externally)
resource "google_cloud_run_v2_job" "ingestion_job" {
  name     = var.ingestion_job_name
  location = var.region
  template {
    template {
      containers {
        image = var.ingestion_image
        env {
          name  = "GCS_BUCKET"
          value = var.gcs_bucket
        }
        env { name = "GCS_PREFIX" value = var.gcs_prefix }
        env { name = "BQ_DATASET" value = var.bq_dataset }
        env { name = "BQ_PROJECT" value = var.project_id }
      }
      service_account = google_service_account.ingestion.email
    }
  }
}

# Cloud Scheduler direct HTTP trigger of the Cloud Run Job (run endpoint)
resource "google_cloud_scheduler_job" "daily_ingestion" {
  name        = "${var.ingestion_job_name}-daily"
  description = "Daily sensor ingestion trigger (HTTP)"
  schedule    = var.ingestion_cron
  time_zone   = var.cron_timezone
  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.ingestion_job.name}:run"
    oidc_token {
      service_account_email = google_service_account.ingestion.email
    }
    headers = {
      Content-Type = "application/json"
    }
    body = base64encode("{}")
  }
}

