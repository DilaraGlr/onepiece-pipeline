# ============================================================
# SERVICE ACCOUNTS
# ============================================================

# 1. Service Account pour Cloud Scheduler
resource "google_service_account" "scheduler" {
  account_id   = "sa-scheduler"
  display_name = "Service Account for Cloud Scheduler"
  description  = "Declenche le workflow"
}

# Permissions pour déclencher le workflow
resource "google_project_iam_member" "scheduler_workflow_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}

# ============================================================

# 2. Service Account pour Workflows
resource "google_service_account" "workflow" {
  account_id   = "sa-workflow"
  display_name = "Service Account for Workflows"
  description  = "Orchestre les jobs Cloud Run"
}

# Permissions pour invoquer les jobs Cloud Run
resource "google_project_iam_member" "workflow_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.workflow.email}"
}

# Permissions pour voir les jobs Cloud Run
resource "google_project_iam_member" "workflow_run_viewer" {
  project = var.project_id
  role    = "roles/run.viewer"
  member  = "serviceAccount:${google_service_account.workflow.email}"
}

# Permissions pour écrire les logs
resource "google_project_iam_member" "workflow_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.workflow.email}"
}

# ============================================================

# 3. Service Account pour jobs data (scraper + OCR)
resource "google_service_account" "job_data" {
  account_id   = "sa-job-data"
  display_name = "Service Account for Data Jobs"
  description  = "Scraper et OCR - acces BigQuery, GCS et secrets"
}

# Permissions BigQuery
resource "google_project_iam_member" "job_data_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.job_data.email}"
}

resource "google_project_iam_member" "job_data_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"  # MOINDRE PRIVILÈGE : peut uniquement lancer des requêtes
  member  = "serviceAccount:${google_service_account.job_data.email}"
}

# Permissions GCS - UNIQUEMENT sur le bucket onepiece-manga-images
# MOINDRE PRIVILÈGE : Accès uniquement au bucket nécessaire, pas tous les buckets du projet
resource "google_storage_bucket_iam_member" "job_data_manga_images" {
  bucket = google_storage_bucket.manga_images.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.job_data.email}"
}

# Permissions Secret Manager - MOINDRE PRIVILÈGE
# job_data a accès UNIQUEMENT au secret Gemini (pour OCR)
# Il NE PEUT PAS accéder au secret Anthropic (pas besoin!)
resource "google_secret_manager_secret_iam_member" "job_data_gemini_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.job_data.email}"
}

# ============================================================

# 4. Service Account pour pipeline NLP
resource "google_service_account" "job_nlp" {
  account_id   = "sa-job-nlp"
  display_name = "Service Account for NLP Pipeline"
  description  = "Pipeline NLP - acces BigQuery et secrets"
}

# Permissions BigQuery
resource "google_project_iam_member" "job_nlp_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.job_nlp.email}"
}

resource "google_project_iam_member" "job_nlp_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"  # MOINDRE PRIVILÈGE : peut uniquement lancer des requêtes
  member  = "serviceAccount:${google_service_account.job_nlp.email}"
}

# Permissions Secret Manager - MOINDRE PRIVILÈGE
# job_nlp a accès UNIQUEMENT au secret Anthropic (Claude API)
# Il NE PEUT PAS accéder au secret Gemini (pas besoin!)
resource "google_secret_manager_secret_iam_member" "job_nlp_anthropic_access" {
  secret_id = google_secret_manager_secret.anthropic_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.job_nlp.email}"
}

# ============================================================

# 5. Service Account pour Dashboard (lecture seule)
resource "google_service_account" "dashboard" {
  account_id   = "sa-dashboard"
  display_name = "Service Account for Dashboard"
  description  = "Dashboard - lecture seule BigQuery"
}

# Permissions BigQuery (lecture seule)
resource "google_project_iam_member" "dashboard_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.dashboard.email}"
}

resource "google_project_iam_member" "dashboard_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"  # MOINDRE PRIVILÈGE : peut uniquement lancer des requêtes
  member  = "serviceAccount:${google_service_account.dashboard.email}"
}

# ============================================================

# 6. Service Account pour Budget Killer Function
resource "google_service_account" "budget_killer" {
  account_id   = "sa-budget-killer"
  display_name = "Service Account for Budget Killer Function"
  description  = "Detache la facturation quand le budget atteint 100%"
}

# Permission pour détacher la facturation du projet
# MOINDRE PRIVILÈGE (Chapitre 2) :
# - roles/billing.projectManager permet UNIQUEMENT de modifier le lien billing
#   entre le projet et le compte de facturation (attach/detach)
# - Ce rôle NE PERMET PAS de modifier les données du projet, créer des ressources,
#   ou accéder aux données (contrairement à Owner/Editor qui sont trop larges)
# - C'est le rôle MINIMAL nécessaire pour la fonction stop_billing() qui appelle
#   cloudbilling.projects.updateBillingInfo avec billingAccountName=""
# - Alternative rejetée: roles/owner ou roles/editor seraient des sur-privilèges
#   dangereux pour une fonction automatisée
resource "google_project_iam_member" "budget_killer_billing_manager" {
  project = var.project_id
  role    = "roles/billing.projectManager"
  member  = "serviceAccount:${google_service_account.budget_killer.email}"
}
