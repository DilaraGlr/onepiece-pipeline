# ============================================================
# BILLING BUDGET & ALERTES
# ============================================================
#
# Ce budget surveille les coûts du projet et envoie des alertes
# pour éviter les dépassements imprévus.
#
# Pourquoi c'est important ?
# - Protection contre les coûts inattendus (bugs, boucles infinies)
# - Surveillance des APIs payantes (Gemini, Claude)
# - Contrôle des ressources Cloud Run et BigQuery
#
# Comment ça marche ?
# - Le budget est calculé mensuellement
# - Des alertes sont envoyées aux seuils : 50%, 90%, 100%
# - Vous recevez un email à chaque seuil atteint
# ============================================================

# Topic Pub/Sub pour recevoir les notifications de budget
resource "google_pubsub_topic" "budget_alerts" {
  name = "budget-alerts"
}

# Abonnement au topic pour les notifications par email
# (optionnel - peut être remplacé par une Cloud Function)
resource "google_pubsub_subscription" "budget_alerts_sub" {
  name  = "budget-alerts-subscription"
  topic = google_pubsub_topic.budget_alerts.name

  # Les messages sont conservés 7 jours
  message_retention_duration = "604800s"

  # Acknowledge deadline de 10 secondes
  ack_deadline_seconds = 10
}

# Budget avec alertes à 50%, 90% et 100%
resource "google_billing_budget" "project_budget" {
  # Nom du compte de facturation Google Cloud
  # À remplacer par votre Billing Account ID
  # Trouvez-le dans : https://console.cloud.google.com/billing
  billing_account = var.billing_account_id

  display_name = "Budget mensuel OneP iece Pipeline"

  # Configuration du budget
  budget_filter {
    # Appliqué uniquement à ce projet
    projects = ["projects/${data.google_project.current.number}"]

    # Filtrer sur tous les services (optionnel)
    # services = ["services/..."]

    # Options supplémentaires :
    # - calendar_period = "MONTH" (par défaut)
    # - credit_types_treatment = "INCLUDE_ALL_CREDITS" (inclut les crédits gratuits)
  }

  # Montant du budget mensuel
  amount {
    specified_amount {
      currency_code = "EUR"  # ou "USD" selon votre compte
      units         = var.monthly_budget_amount
    }
  }

  # Alertes aux seuils définis
  threshold_rules {
    threshold_percent = 0.5  # 50% du budget
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.9  # 90% du budget
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0  # 100% du budget
    spend_basis       = "CURRENT_SPEND"
  }

  # Configuration des notifications
  all_updates_rule {
    # Pub/Sub topic pour recevoir les notifications
    pubsub_topic = google_pubsub_topic.budget_alerts.id

    # Schéma de notification (optionnel)
    # schema_version = "1.0"

    # Désactiver les notifications par email si vous utilisez Pub/Sub
    disable_default_iam_recipients = false

    # Emails supplémentaires à notifier (optionnel)
    # monitoring_notification_channels = [...]
  }
}

# Data source pour récupérer le numéro du projet
data "google_project" "current" {
  project_id = var.project_id
}

# ============================================================
# CLOUD FUNCTION - BUDGET KILLER
# ============================================================
# Détache automatiquement la facturation quand le budget atteint 100%

# Bucket GCS pour stocker les sources des Cloud Functions
resource "google_storage_bucket" "functions_source" {
  name          = "${var.project_id}-functions-source"
  location      = var.region
  force_destroy = true

  labels = {
    app = "onepiece"
  }

  uniform_bucket_level_access = true
}

# Archiver le code de la fonction
data "archive_file" "budget_killer_source" {
  type        = "zip"
  source_dir  = "${path.module}/../functions/kill-billing"
  output_path = "${path.module}/../functions/kill-billing.zip"
}

# Uploader le zip vers GCS
resource "google_storage_bucket_object" "budget_killer_zip" {
  name   = "kill-billing-${data.archive_file.budget_killer_source.output_md5}.zip"
  bucket = google_storage_bucket.functions_source.name
  source = data.archive_file.budget_killer_source.output_path
}

# Cloud Function 2e génération
resource "google_cloudfunctions2_function" "budget_killer" {
  name        = "budget-killer"
  location    = var.region
  description = "Detache la facturation du projet quand le budget atteint 100%"

  build_config {
    runtime     = "python312"
    entry_point = "stop_billing"

    source {
      storage_source {
        bucket = google_storage_bucket.functions_source.name
        object = google_storage_bucket_object.budget_killer_zip.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "256M"
    timeout_seconds    = 60

    service_account_email = google_service_account.budget_killer.email

    environment_variables = {
      GCP_PROJECT = var.project_id
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic          = google_pubsub_topic.budget_alerts.id
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.budget_killer.email
  }

  labels = {
    app = "onepiece"
  }
}

# Permission pour que Pub/Sub puisse invoquer la fonction
resource "google_cloud_run_service_iam_member" "budget_killer_invoker" {
  location = google_cloudfunctions2_function.budget_killer.location
  service  = google_cloudfunctions2_function.budget_killer.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.budget_killer.email}"
}
