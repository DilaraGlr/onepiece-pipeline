# ============================================================
# CLOUD BUILD - CI/CD AUTOMATION
# ============================================================
# Ce fichier configure l'automatisation du déploiement via Cloud Build
# Déclenché à chaque git push sur la branche main du repo GitHub
#
# Architecture :
# git push main → GitHub → Cloud Build Trigger → cloudbuild.yaml
#   → Build Docker images → Push to Artifact Registry → Terraform apply
# ============================================================

# ============================================================
# CLOUD BUILD TRIGGER
# ============================================================
# Déclenche automatiquement le build à chaque push sur main
#
# ⚠️ CRÉATION MANUELLE REQUISE :
# Le repository GitHub est connecté via GitHub App (ancienne méthode)
# qui n'est pas directement supportée par Terraform.
#
# Pour créer le trigger manuellement :
# 1. Aller sur : https://console.cloud.google.com/cloud-build/triggers?project=onepiece-pipeline
# 2. Cliquer "CREATE TRIGGER"
# 3. Nom : onepiece-deploy-main
# 4. Event : Push to a branch
# 5. Repository : DilaraGlr/onepiece-pipeline (déjà connecté)
# 6. Branch : ^main$
# 7. Configuration : Cloud Build configuration file (YAML or JSON)
# 8. Location : Repository / cloudbuild.yaml
# 9. Cliquer "CREATE"
#
# Pour importer ensuite dans Terraform (optionnel) :
# terraform import google_cloudbuild_trigger.onepiece_deploy projects/onepiece-pipeline/locations/global/triggers/TRIGGER_ID

# Ressource commentée pour l'instant - créer manuellement via la console
# resource "google_cloudbuild_trigger" "onepiece_deploy" {
#   name        = "onepiece-deploy-main"
#   description = "Déploiement automatique du pipeline One Piece à chaque push sur main"
#   filename    = "cloudbuild.yaml"
# }

# ============================================================
# SERVICE ACCOUNT CLOUD BUILD
# ============================================================
# Service account dédié pour Cloud Build (au lieu du SA système)
#
# Ce compte a besoin de permissions spécifiques pour :
# 1. Pusher les images Docker vers Artifact Registry
# 2. Déployer sur Cloud Run
# 3. Agir en tant que les service accounts des jobs
# 4. Lire/écrire le state Terraform dans GCS
# 5. Écrire les logs de build
# ============================================================

resource "google_service_account" "cloudbuild" {
  account_id   = "sa-cloudbuild"
  display_name = "Service Account for Cloud Build"
  description  = "SA utilisé par Cloud Build pour builder et déployer"
}

# ============================================================
# PERMISSION 1/5 : Artifact Registry Writer
# ============================================================
# Permet à Cloud Build de pusher les images Docker buildées

resource "google_project_iam_member" "cloudbuild_artifactregistry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# PERMISSION 2/5 : Cloud Run Developer
# ============================================================
# Permet à Cloud Build de déployer/modifier les jobs et services Cloud Run
# Nécessaire pour que terraform apply puisse créer/mettre à jour :
# - google_cloud_run_v2_job.scraper
# - google_cloud_run_v2_job.ocr
# - google_cloud_run_v2_job.nlp
# - google_cloud_run_v2_service.dashboard

resource "google_project_iam_member" "cloudbuild_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# PERMISSION 3/5 : Service Account User
# ============================================================
# Permet à Cloud Build d'agir en tant que les service accounts des jobs
# Sans cette permission, Cloud Build ne peut pas créer de ressources
# qui utilisent un service account personnalisé (sa-job-data, sa-job-nlp, etc.)

resource "google_project_iam_member" "cloudbuild_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# PERMISSION 4/5 : Storage Admin sur le bucket tfstate
# ============================================================
# Permet à Cloud Build de lire/écrire le state Terraform
# Nécessaire pour que terraform init/apply puisse fonctionner

resource "google_storage_bucket_iam_member" "cloudbuild_tfstate_admin" {
  bucket = "onepiece-tfstate"
  role   = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# PERMISSION 5/5 : Logs Writer
# ============================================================
# Permet à Cloud Build d'écrire les logs de build dans Cloud Logging

resource "google_project_iam_member" "cloudbuild_logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# PERMISSIONS SUPPLÉMENTAIRES POUR TERRAFORM
# ============================================================
# Cloud Build (via Terraform) a besoin de créer/modifier diverses ressources

# Permissions BigQuery
resource "google_project_iam_member" "cloudbuild_bigquery_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Permissions Cloud Scheduler
resource "google_project_iam_member" "cloudbuild_cloudscheduler_admin" {
  project = var.project_id
  role    = "roles/cloudscheduler.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Permissions Secret Manager
resource "google_project_iam_member" "cloudbuild_secretmanager_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Permissions Workflows
resource "google_project_iam_member" "cloudbuild_workflows_admin" {
  project = var.project_id
  role    = "roles/workflows.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Permissions IAM (pour gérer les service accounts et leurs bindings)
resource "google_project_iam_member" "cloudbuild_iam_admin" {
  project = var.project_id
  role    = "roles/iam.securityAdmin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# OUTPUTS
# ============================================================

# Outputs commentés car le trigger est créé manuellement
# output "cloudbuild_trigger_name" {
#   description = "Nom du trigger Cloud Build"
#   value       = google_cloudbuild_trigger.onepiece_deploy.name
# }

# output "cloudbuild_trigger_id" {
#   description = "ID du trigger Cloud Build"
#   value       = google_cloudbuild_trigger.onepiece_deploy.trigger_id
# }

output "cloudbuild_service_account" {
  description = "Service account utilisé par Cloud Build"
  value       = google_service_account.cloudbuild.email
}

# ============================================================
# DOCUMENTATION
# ============================================================

# Comment voir les builds Cloud Build ?
#
# 1. Via la console GCP :
#    https://console.cloud.google.com/cloud-build/builds?project=onepiece-pipeline
#
# 2. Via gcloud CLI :
#    gcloud builds list --limit=10
#    gcloud builds log <BUILD_ID>
#
# 3. Déclencher un build manuellement :
#    gcloud builds triggers run onepiece-deploy-main --branch=main
#
# Comment connecter le repo GitHub ?
#
# 1. Aller sur : https://console.cloud.google.com/cloud-build/triggers
# 2. Cliquer "Connect Repository"
# 3. Sélectionner "GitHub (Cloud Build GitHub App)"
# 4. Autoriser l'accès au repo DilaraGlr/onepiece-pipeline
# 5. Le trigger sera automatiquement créé par Terraform après
#
# Sécurité :
# - Le SA Cloud Build a des permissions larges (admin sur plusieurs services)
# - C'est acceptable car il n'est utilisé QUE par Cloud Build (pas par des humains)
# - Les builds sont déclenchés uniquement sur push main (code reviewé)
# - Pour renforcer : utiliser des branch protection rules sur GitHub (require PR review)
