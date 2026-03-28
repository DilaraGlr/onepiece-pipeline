output "bigquery_dataset" {
  description = "Le dataset BigQuery créé"
  value       = google_bigquery_dataset.onepiece.dataset_id
}

output "bigquery_table" {
  description = "La table BigQuery créée"
  value       = google_bigquery_table.chapters.table_id
}

output "cloud_run_job" {
  description = "Le nom du Cloud Run Job"
  value       = google_cloud_run_v2_job.scraper.name
}

output "scheduler" {
  description = "Le nom du Cloud Scheduler"
  value       = google_cloud_scheduler_job.weekly.name
}
