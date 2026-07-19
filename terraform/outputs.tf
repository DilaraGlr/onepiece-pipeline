output "bigquery_dataset" {
  value = google_bigquery_dataset.onepiece.dataset_id
}

output "bigquery_dataset_pipeline_logs" {
  value       = google_bigquery_dataset.pipeline_logs.dataset_id
  description = "Dataset BigQuery pour stocker les logs des Cloud Run jobs"
}

output "bigquery_table_chapters" {
  value = google_bigquery_table.chapters.table_id
}

output "bigquery_table_dialogues" {
  value = google_bigquery_table.dialogues.table_id
}

output "bigquery_table_speakers" {
  value = google_bigquery_table.speakers.table_id
}

output "gcs_bucket" {
  value = google_storage_bucket.manga_images.name
}

output "cloud_run_scraper" {
  value = google_cloud_run_v2_job.scraper.name
}

output "cloud_run_ocr" {
  value = google_cloud_run_v2_job.ocr.name
}

output "cloud_run_nlp" {
  value = google_cloud_run_v2_job.nlp.name
}

output "cloud_run_dashboard" {
  value = google_cloud_run_v2_service.dashboard.name
}

output "dashboard_url" {
  value       = google_cloud_run_v2_service.dashboard.uri
  description = "URL publique du dashboard One Piece"
}

output "scheduler" {
  value = google_cloud_scheduler_job.weekly.name
}

output "deployed_image_tag" {
  value       = var.image_tag
  description = "Tag Docker déployé (hash Git ou 'latest')"
}

output "budget_topic" {
  value       = google_pubsub_topic.budget_alerts.name
  description = "Topic Pub/Sub pour les alertes de budget"
}

output "budget_name" {
  value       = google_billing_budget.project_budget.display_name
  description = "Nom du budget mensuel configuré"
}

output "budget_killer_function" {
  value       = google_cloudfunctions2_function.budget_killer.name
  description = "Cloud Function qui détache la facturation à 100% du budget"
}