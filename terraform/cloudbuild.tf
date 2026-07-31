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
# PERMISSIONS CLOUD BUILD - RÔLES PRÉCIS
# ============================================================
# Le SA Cloud Build utilise des rôles prédéfinis précis pour chaque service
# géré par Terraform, conformément au principe de moindre privilège (chapitre 2).
#
# Ce SA est utilisé UNIQUEMENT par le pipeline Cloud Build automatisé (jamais
# par un humain), ce qui limite les risques liés à ces permissions.

# ============================================================
# ARTIFACT REGISTRY
# ============================================================
# Nécessaire pour : cloudbuild.yaml étapes 1-6 (build et push des 3 images Docker)
# Permet de créer le repository onepiece-repo et pusher les images
resource "google_project_iam_member" "cloudbuild_artifactregistry" {
  project = var.project_id
  role    = "roles/artifactregistry.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# CLOUD RUN
# ============================================================
# Nécessaire pour : terraform apply sur google_cloud_run_v2_job (scraper, ocr, nlp)
# et google_cloud_run_v2_service (dashboard)
# Permet de créer, modifier, déployer les jobs et services Cloud Run
resource "google_project_iam_member" "cloudbuild_run" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# BIGQUERY
# ============================================================
# Nécessaire pour : terraform apply sur google_bigquery_dataset (onepiece, pipeline_logs,
# billing_export) et google_bigquery_table (chapters, dialogues, speakers)
# Permet de créer et gérer les datasets et tables BigQuery
resource "google_project_iam_member" "cloudbuild_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# GOOGLE CLOUD STORAGE
# ============================================================
# Nécessaire pour : terraform apply sur google_storage_bucket (manga_images,
# functions_source) et google_storage_bucket_object (budget_killer_zip)
# Permet de créer et gérer les buckets applicatifs
# NOTE : storage.buckets.create (nécessaire pour créer des buckets) n'est disponible
# que dans roles/storage.admin au niveau projet (pas de rôle prédéfini plus restreint)
resource "google_project_iam_member" "cloudbuild_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# SECRET MANAGER
# ============================================================
# Nécessaire pour : terraform apply sur google_secret_manager_secret (anthropic-api-key,
# gemini-api-key)
# Permet de créer les secrets (pas d'accès aux valeurs secrètes)
resource "google_project_iam_member" "cloudbuild_secretmanager" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# CLOUD SCHEDULER
# ============================================================
# Nécessaire pour : terraform apply sur google_cloud_scheduler_job (onepiece-scheduler)
# Permet de créer et gérer le scheduler hebdomadaire
resource "google_project_iam_member" "cloudbuild_scheduler" {
  project = var.project_id
  role    = "roles/cloudscheduler.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# CLOUD WORKFLOWS
# ============================================================
# Nécessaire pour : terraform apply sur google_workflows_workflow (onepiece-workflow)
# Permet de créer et déployer le workflow d'orchestration
resource "google_project_iam_member" "cloudbuild_workflows" {
  project = var.project_id
  role    = "roles/workflows.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# PUB/SUB
# ============================================================
# Nécessaire pour : terraform apply sur google_pubsub_topic.budget_alerts
# et google_pubsub_subscription.budget_alerts_sub (terraform/budget.tf)
# Permet de créer les topics et subscriptions Pub/Sub
# roles/pubsub.editor suffit (pas besoin de .admin car on ne gère pas l'IAM sur les topics)
resource "google_project_iam_member" "cloudbuild_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.editor"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# CLOUD FUNCTIONS
# ============================================================
# Nécessaire pour : terraform apply sur google_cloudfunctions2_function.budget_killer
# (terraform/budget.tf)
# Permet de créer et déployer la Cloud Function v2
# roles/cloudfunctions.developer suffit (l'IAM sur le service Cloud Run de la fonction
# est géré par roles/run.admin, pas par cloudfunctions)
resource "google_project_iam_member" "cloudbuild_functions" {
  project = var.project_id
  role    = "roles/cloudfunctions.developer"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# MONITORING
# ============================================================
# Nécessaire pour : terraform apply sur google_monitoring_notification_channel,
# google_monitoring_alert_policy, google_monitoring_uptime_check_config,
# google_monitoring_dashboard (terraform/monitoring.tf)
# Permet de créer et gérer les alertes et dashboards de monitoring
# roles/monitoring.editor suffit (pas de gestion IAM sur les ressources monitoring)
resource "google_project_iam_member" "cloudbuild_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.editor"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# LOGGING
# ============================================================
# Nécessaire pour : terraform apply sur google_logging_metric (cloud_run_job_errors,
# roi_des_pirates_mentions) et google_logging_project_sink (cloud_run_jobs_to_bigquery,
# audit_logs_to_bigquery) dans terraform/monitoring.tf et terraform/audit.tf
# Permet de créer et gérer les log sinks et métriques log-based
# roles/logging.configWriter suffit (crée sinks et métriques ; l'IAM sur les datasets
# BigQuery cibles est géré via roles/resourcemanager.projectIamAdmin)
resource "google_project_iam_member" "cloudbuild_logging" {
  project = var.project_id
  role    = "roles/logging.configWriter"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# ============================================================
# SERVICE ACCOUNTS - CRÉATION
# ============================================================
# Nécessaire pour : terraform apply sur google_service_account (scheduler, workflow,
# job_data, job_nlp, dashboard, budget_killer)
# Permet de créer et gérer les service accounts du projet
# CONDITION IAM : Restreint aux service accounts avec le préfixe "sa-" (convention du projet)
resource "google_project_iam_member" "cloudbuild_serviceaccount_admin" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"

  condition {
    title       = "Only manage onepiece service accounts"
    description = "Restreint la gestion aux service accounts avec préfixe sa-"
    expression  = "resource.name.startsWith('projects/${var.project_id}/serviceAccounts/sa-')"
  }
}

# ============================================================
# IAM BINDINGS - GESTION DES PERMISSIONS DES SERVICE ACCOUNTS
# ============================================================
# Nécessaire pour : terraform apply sur google_project_iam_member et google_*_iam_member
# définis dans service_accounts.tf, budget.tf, monitoring.tf, audit.tf
# Permet de donner des rôles AUX service accounts (ex: bigquery.dataEditor au SA scraper)
# et de gérer les IAM bindings sur les ressources (buckets GCS, secrets, datasets BigQuery)
#
# LIMITATION TECHNIQUE DES CONDITIONS IAM :
# Il est IMPOSSIBLE de restreindre ce rôle pour qu'il ne puisse créer des bindings que
# pour certains membres (ex: uniquement les SA avec préfixe sa-). Les conditions IAM
# permettent de filtrer sur resource.* (la ressource affectée) mais PAS sur le membre
# cible du binding IAM. GCP ne fournit pas d'attribut request.member ou equivalent.
#
# CONSÉQUENCE : Le SA Cloud Build peut techniquement donner n'importe quel rôle à
# n'importe quel membre (y compris à lui-même ou à un compte externe).
#
# MITIGATIONS (chapitre 2 - moindre privilège) :
# 1. Ce SA est utilisé UNIQUEMENT par Cloud Build (pas par des humains)
# 2. Les builds sont déclenchés uniquement sur push main (code reviewé via PR)
# 3. Branch protection rules GitHub : require PR review avant merge sur main
# 4. Audit logs activés (audit.tf) pour tracer toutes les modifications IAM
# 5. Alternative rejetée : créer les bindings IAM manuellement (hors Terraform)
#    casse le principe "Infrastructure as Code"
resource "google_project_iam_member" "cloudbuild_iam_admin" {
  project = var.project_id
  role    = "roles/resourcemanager.projectIamAdmin"
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
