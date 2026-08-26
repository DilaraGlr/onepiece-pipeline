# ============================================================
# DATAFORM REPOSITORY
# ============================================================
# Repository Dataform pour transformer les données brutes
# (chapters, dialogues, speakers) en tables agrégées prêtes
# pour l'analyse et le dashboard.
#
# Modèles SQL versionnés dans dataform/definitions/
# ============================================================

resource "google_dataform_repository" "onepiece_transformations" {
  provider = google-beta

  name   = "onepiece-transformations"
  region = var.region # europe-west1

  # Configuration workspace pour développement local
  workspace_compilation_overrides {
    default_database = var.project_id
    # Suffixe _dev pour isoler les tests locaux des tables de production
    schema_suffix = "_dev"
  }

  # Connexion au code source (Git) - optionnel pour démarrer
  # git_remote_settings {
  #   url = "https://github.com/DilaraGlr/onepiece-pipeline.git"
  #   default_branch = "main"
  #   authentication_token_secret_version = "projects/${var.project_id}/secrets/github-token/versions/latest"
  # }
}

# Dataset pour stocker les assertions de qualité Dataform
resource "google_bigquery_dataset" "dataform_assertions" {
  dataset_id = "dataform_assertions"
  location   = "EU"

  labels = {
    app = "onepiece"
  }

  description = "Dataset pour stocker les assertions de qualité Dataform (unicité, non-nullité, etc.)"
}

# Service account pour exécuter les workflows Dataform
resource "google_service_account" "dataform" {
  account_id   = "sa-dataform"
  display_name = "Service Account pour Dataform (transformations SQL)"
  description  = "Exécute les workflows Dataform : transformations SQL sur BigQuery"
}

# ============================================================
# PERMISSIONS SCOPÉES AU DATASET (PRINCIPE DU MOINDRE PRIVILÈGE)
# ============================================================

# Permission BigQuery : lecture/écriture sur le dataset onepiece
# (pour lire les tables source chapters/dialogues/speakers et créer les tables agrégées)
resource "google_bigquery_dataset_iam_member" "dataform_onepiece_editor" {
  dataset_id = google_bigquery_dataset.onepiece.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.dataform.email}"
}

# Permission BigQuery : lecture/écriture sur le dataset dataform_assertions
# (pour créer et mettre à jour les tables d'assertions de qualité)
resource "google_bigquery_dataset_iam_member" "dataform_assertions_editor" {
  dataset_id = google_bigquery_dataset.dataform_assertions.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.dataform.email}"
}

# ============================================================
# PERMISSIONS AU NIVEAU PROJET (NÉCESSAIRES, NON SCOPABLES)
# ============================================================

# Permission BigQuery : création de jobs
# NOTE : bigquery.jobUser ne peut PAS être scopé au dataset, doit être au niveau projet
resource "google_project_iam_member" "dataform_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dataform.email}"
}

# Permission Dataform : exécuter les workflows
resource "google_project_iam_member" "dataform_workflow_invoker" {
  project = var.project_id
  role    = "roles/dataform.workflowInvoker"
  member  = "serviceAccount:${google_service_account.dataform.email}"
}
