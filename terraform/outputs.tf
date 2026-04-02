output "bigquery_dataset" {
  value = google_bigquery_dataset.onepiece.dataset_id
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