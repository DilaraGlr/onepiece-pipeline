# ============================================================
# MONITORING & ALERTING
# ============================================================
# Configuration des canaux de notification pour les alertes

# ============================================================
# NOTIFICATION CHANNEL - EMAIL
# ============================================================
# Canal de notification par email pour recevoir les alertes
# du projet (erreurs, budgets, incidents)

resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Dilara"
  type         = "email"

  labels = {
    email_address = "guler.dilara2000@gmail.com"
  }

  enabled = true
}

# ============================================================
# ALERTING POLICY - CLOUD RUN JOB FAILURES
# ============================================================
# Alerte déclenchée quand une exécution de Cloud Run job échoue
# Surveille les jobs : scraper, ocr, nlp

resource "google_monitoring_alert_policy" "cloud_run_job_failure" {
  display_name = "Cloud Run Job Failure"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Cloud Run Job execution failed"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_job\" AND metric.type=\"run.googleapis.com/job/completed_execution_count\" AND metric.labels.result=\"failed\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email.id
  ]

  alert_strategy {
    auto_close = "86400s" # Ferme automatiquement après 24h
  }

  documentation {
    content = <<-EOT
    ## Cloud Run Job Failure Alert

    Une exécution de Cloud Run job a échoué.

    **Jobs surveillés:**
    - onepiece-scraper-job
    - ocr-pipeline-job
    - nlp-pipeline-job

    **Actions à prendre:**
    1. Vérifier les logs du job dans Cloud Logging
    2. Identifier la cause de l'échec (erreur API, timeout, permissions, etc.)
    3. Corriger le problème et relancer manuellement si nécessaire

    **Liens utiles:**
    - [Cloud Run Jobs Console](https://console.cloud.google.com/run/jobs?project=t-lexicon-231513)
    - [Cloud Logging](https://console.cloud.google.com/logs?project=t-lexicon-231513)
    EOT
  }
}

# ============================================================
# LOG-BASED METRIC - CLOUD RUN JOB ERRORS
# ============================================================
# Métrique custom qui compte les logs d'erreur (severity >= ERROR)
# provenant des Cloud Run jobs

resource "google_logging_metric" "cloud_run_job_errors" {
  name   = "cloud_run_job_errors"
  filter = <<-EOT
    resource.type="cloud_run_job"
    severity>=ERROR
  EOT

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"

    labels {
      key         = "job_name"
      value_type  = "STRING"
      description = "Nom du Cloud Run job"
    }

    labels {
      key         = "severity"
      value_type  = "STRING"
      description = "Niveau de sévérité du log"
    }

    display_name = "Cloud Run Job Errors"
  }

  label_extractors = {
    "job_name" = "EXTRACT(resource.labels.job_name)"
    "severity" = "EXTRACT(severity)"
  }
}

# ============================================================
# LOG SINK - CLOUD RUN JOBS TO BIGQUERY
# ============================================================
# Exporte tous les logs des Cloud Run jobs vers BigQuery
# pour analyse et archivage à long terme

resource "google_logging_project_sink" "cloud_run_jobs_to_bigquery" {
  name        = "cloud-run-jobs-to-bigquery"
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.pipeline_logs.dataset_id}"

  # Filtre pour capturer tous les logs des Cloud Run jobs
  filter = <<-EOT
    resource.type="cloud_run_job"
    (resource.labels.job_name="onepiece-scraper-job" OR
     resource.labels.job_name="ocr-pipeline-job" OR
     resource.labels.job_name="nlp-pipeline-job")
  EOT

  # Utilise l'ID unique du service writer pour les permissions
  unique_writer_identity = true

  bigquery_options {
    use_partitioned_tables = true
  }
}

# Permissions pour que le sink puisse écrire dans BigQuery
resource "google_bigquery_dataset_iam_member" "pipeline_logs_writer" {
  dataset_id = google_bigquery_dataset.pipeline_logs.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.cloud_run_jobs_to_bigquery.writer_identity
}

# ============================================================
# UPTIME CHECK - DASHBOARD
# ============================================================
# Vérifie la disponibilité du dashboard toutes les minutes
# Timeout de 10 secondes par vérification

resource "google_monitoring_uptime_check_config" "dashboard" {
  display_name = "Dashboard Uptime Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "onepiece-dashboard-37i2wtwxfa-ew.a.run.app"
    }
  }
}

# ============================================================
# ALERTING POLICY - DASHBOARD DOWNTIME
# ============================================================
# Alerte déclenchée si le dashboard est indisponible plus de 5 minutes

resource "google_monitoring_alert_policy" "dashboard_downtime" {
  display_name = "Dashboard Downtime Alert"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Dashboard indisponible"

    condition_threshold {
      filter          = "resource.type=\"uptime_url\" AND metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.labels.host=\"onepiece-dashboard-37i2wtwxfa-ew.a.run.app\""
      duration        = "300s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.host"]
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email.id
  ]

  alert_strategy {
    auto_close = "86400s"
  }

  documentation {
    content = <<-EOT
    ## Dashboard Downtime Alert

    Le dashboard One Piece est indisponible depuis plus de 5 minutes.

    **URL:** https://onepiece-dashboard-37i2wtwxfa-ew.a.run.app

    **Actions à prendre:**
    1. Vérifier les logs du service Cloud Run
    2. Vérifier que le service est bien déployé et qu'il a des instances running
    3. Tester manuellement l'URL dans un navigateur
    4. Vérifier les quotas et limites du projet

    **Liens utiles:**
    - [Cloud Run Dashboard Console](https://console.cloud.google.com/run/detail/europe-west1/onepiece-dashboard?project=t-lexicon-231513)
    - [Cloud Logging](https://console.cloud.google.com/logs?project=t-lexicon-231513)
    - [Uptime Checks](https://console.cloud.google.com/monitoring/uptime?project=t-lexicon-231513)
    EOT
  }
}

# ============================================================
# OUTPUTS
# ============================================================

output "notification_channel_email" {
  description = "ID du canal de notification email"
  value       = google_monitoring_notification_channel.email.id
}

output "alert_policy_job_failure" {
  description = "ID de la policy d'alerte pour les échecs de jobs"
  value       = google_monitoring_alert_policy.cloud_run_job_failure.id
}

output "log_metric_job_errors" {
  description = "Nom de la métrique log-based pour les erreurs de jobs"
  value       = google_logging_metric.cloud_run_job_errors.name
}

output "uptime_check_dashboard" {
  description = "ID de l'uptime check pour le dashboard"
  value       = google_monitoring_uptime_check_config.dashboard.id
}

output "alert_policy_dashboard_downtime" {
  description = "ID de la policy d'alerte pour l'indisponibilité du dashboard"
  value       = google_monitoring_alert_policy.dashboard_downtime.id
}

output "log_sink_cloud_run_jobs" {
  description = "Nom du log sink pour exporter les logs des Cloud Run jobs vers BigQuery"
  value       = google_logging_project_sink.cloud_run_jobs_to_bigquery.name
}
