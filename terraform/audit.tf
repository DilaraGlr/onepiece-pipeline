# ============================================================
# AUDIT LOGS CONFIGURATION
# ============================================================

# Active les Data Access Logs pour tous les services critiques
# Cela permet de tracer QUI a fait QUOI, QUAND sur les ressources sensibles

# BigQuery Audit Logs
resource "google_project_iam_audit_config" "bigquery_audit" {
  project = var.project_id
  service = "bigquery.googleapis.com"

  audit_log_config {
    log_type = "DATA_READ"
  }
  audit_log_config {
    log_type = "DATA_WRITE"
  }
  audit_log_config {
    log_type = "ADMIN_READ"
  }
}

# Cloud Storage Audit Logs
resource "google_project_iam_audit_config" "storage_audit" {
  project = var.project_id
  service = "storage.googleapis.com"

  audit_log_config {
    log_type = "DATA_READ"
  }
  audit_log_config {
    log_type = "DATA_WRITE"
  }
  audit_log_config {
    log_type = "ADMIN_READ"
  }
}

# Secret Manager Audit Logs
resource "google_project_iam_audit_config" "secretmanager_audit" {
  project = var.project_id
  service = "secretmanager.googleapis.com"

  audit_log_config {
    log_type = "DATA_READ"
  }
  audit_log_config {
    log_type = "ADMIN_READ"
  }
}

# Cloud Run Audit Logs
resource "google_project_iam_audit_config" "run_audit" {
  project = var.project_id
  service = "run.googleapis.com"

  audit_log_config {
    log_type = "ADMIN_READ"
  }
}

# ============================================================
# LOGS SINK (Optionnel mais recommandé)
# ============================================================

# Exporter les audit logs vers BigQuery pour analyse
# Permet de faire des requêtes SQL sur les logs
# Exemple : "Qui a accédé à la table speakers le mois dernier ?"

resource "google_logging_project_sink" "audit_logs_to_bigquery" {
  name        = "audit-logs-to-bigquery"
  description = "Exporte les audit logs vers BigQuery pour analyse et retention long terme"

  # Destination : Dataset BigQuery
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.audit_logs.dataset_id}"

  # Filtre : Uniquement les Data Access Logs
  # protoPayload.methodName commence par "google.cloud" = operations d'accès aux données
  filter = <<-EOT
    protoPayload.serviceName=("bigquery.googleapis.com" OR "storage.googleapis.com" OR "secretmanager.googleapis.com")
    AND logName=~".*cloudaudit.googleapis.com.*data_access"
  EOT

  # Unique writer identity : Crée un service account dédié pour écrire dans BigQuery
  unique_writer_identity = true
}

# Dataset BigQuery pour stocker les audit logs
resource "google_bigquery_dataset" "audit_logs" {
  dataset_id  = "audit_logs"
  location    = "US"  # Doit être en US pour les audit logs
  description = "Stockage des audit logs pour analyse et compliance"

  # Retention de 90 jours (obligatoire pour RGPD en général)
  default_table_expiration_ms = 7776000000  # 90 jours en millisecondes
}

# Permission pour le sink d'écrire dans le dataset
resource "google_bigquery_dataset_iam_member" "audit_logs_writer" {
  dataset_id = google_bigquery_dataset.audit_logs.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.audit_logs_to_bigquery.writer_identity
}

# ============================================================
# OUTPUTS
# ============================================================

output "audit_logs_dataset" {
  description = "Dataset BigQuery contenant les audit logs"
  value       = google_bigquery_dataset.audit_logs.dataset_id
}

output "audit_logs_sink" {
  description = "Sink pour exporter les audit logs vers BigQuery"
  value       = google_logging_project_sink.audit_logs_to_bigquery.name
}

# ============================================================
# DOCUMENTATION
# ============================================================

# Comment voir les audit logs dans Cloud Logging ?
#
# 1. Via la console GCP :
#    https://console.cloud.google.com/logs/query?project=onepiece-pipeline
#    Filtre : logName=~"cloudaudit.googleapis.com"
#
# 2. Via gcloud CLI :
#    gcloud logging read "logName=~\"cloudaudit.googleapis.com/data_access\"" --limit=50 --format=json
#
# 3. Via BigQuery (après export) :
#    SELECT
#      timestamp,
#      protopayload_auditlog.authenticationInfo.principalEmail as user,
#      protopayload_auditlog.serviceName as service,
#      protopayload_auditlog.methodName as method,
#      protopayload_auditlog.resourceName as resource
#    FROM `onepiece-pipeline.audit_logs.cloudaudit_googleapis_com_data_access_*`
#    WHERE DATE(_PARTITIONTIME) = CURRENT_DATE()
#    ORDER BY timestamp DESC
#    LIMIT 100;

# Exemples de requêtes d'audit utiles :
#
# Q1 : Qui a accédé au secret gemini-api-key ?
# SELECT
#   timestamp,
#   protopayload_auditlog.authenticationInfo.principalEmail
# FROM `onepiece-pipeline.audit_logs.cloudaudit_googleapis_com_data_access_*`
# WHERE protopayload_auditlog.resourceName LIKE '%gemini-api-key%'
# ORDER BY timestamp DESC;
#
# Q2 : Toutes les modifications sur la table speakers ?
# SELECT
#   timestamp,
#   protopayload_auditlog.authenticationInfo.principalEmail,
#   protopayload_auditlog.methodName
# FROM `onepiece-pipeline.audit_logs.cloudaudit_googleapis_com_data_access_*`
# WHERE protopayload_auditlog.resourceName LIKE '%tables/speakers%'
#   AND protopayload_auditlog.methodName LIKE '%insert%'
# ORDER BY timestamp DESC;
#
# Q3 : Qui a téléchargé des images depuis GCS ?
# SELECT
#   timestamp,
#   protopayload_auditlog.authenticationInfo.principalEmail,
#   protopayload_auditlog.resourceName
# FROM `onepiece-pipeline.audit_logs.cloudaudit_googleapis_com_data_access_*`
# WHERE protopayload_auditlog.serviceName = 'storage.googleapis.com'
#   AND protopayload_auditlog.methodName = 'storage.objects.get'
# ORDER BY timestamp DESC;
