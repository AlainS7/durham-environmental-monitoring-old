variable "project_id" { type = string }
variable "region" { type = string  default = "us-central1" }
variable "gcs_bucket" { type = string }
variable "gcs_prefix" { type = string default = "sensor_readings" }
variable "bq_dataset" { type = string  default = "sensors" }
variable "raw_retention_days" { type = number default = 90 }
variable "ingestion_job_name" { type = string default = "sensor-ingestion-job" }
variable "ingestion_image" { type = string description = "Full artifact registry image reference" }
variable "ingestion_cron" { type = string default = "5 7 * * *" }
variable "cron_timezone" { type = string default = "UTC" }

# Additional maintenance job images (optional if using shared repo + tag)
variable "refresh_job_name" { type = string default = "refresh-partitions" }
variable "refresh_image" { type = string description = "Image for partition refresh job" }
variable "refresh_cron" { type = string default = "0 4 * * *" }

variable "metrics_job_name" { type = string default = "record-metrics" }
variable "metrics_image" { type = string description = "Image for metrics recording job" }
variable "metrics_cron" { type = string default = "10 4 * * *" }

variable "window_days" { type = number default = 7 }

# Artifact Registry (optional create)
variable "create_artifact_repo" { type = bool default = false }
variable "artifact_repo" { type = string default = "weather-maintenance-images" }
