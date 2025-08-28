output "ingestion_service_account" { value = google_service_account.ingestion.email }
output "verifier_service_account" { value = google_service_account.verifier.email }
output "bucket_name" { value = google_storage_bucket.raw_bucket.name }
output "dataset_id" { value = google_bigquery_dataset.sensors.dataset_id }
