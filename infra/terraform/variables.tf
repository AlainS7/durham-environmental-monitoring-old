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
