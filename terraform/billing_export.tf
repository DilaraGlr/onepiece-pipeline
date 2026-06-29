# ============================================================
# EXPORT DE FACTURATION BIGQUERY
# ============================================================
#
# Configure l'export automatique des données de facturation
# vers un dataset BigQuery dédié pour analyse et monitoring.
#
# Avantages :
# - Analyse détaillée des coûts par service, région, SKU
# - Requêtes SQL pour identifier les coûts élevés
# - Intégration avec Data Studio pour dashboards
# - Historique complet de facturation
#
# Types d'exports disponibles :
# 1. Standard Usage Cost (données d'utilisation détaillées)
# 2. Detailed Usage Cost (encore plus granulaire)
# 3. Pricing (données de tarification)
# ============================================================

# Dataset BigQuery pour recevoir les exports de facturation
resource "google_bigquery_dataset" "billing_export" {
  dataset_id                  = "billing_export"
  friendly_name               = "Billing Export Data"
  description                 = "Dataset pour les exports de facturation Google Cloud"
  location                    = "US" # Les exports de facturation doivent être en US ou EU
  default_table_expiration_ms = null # Pas d'expiration automatique des tables

  # Accès au compte de service Cloud Billing pour écrire les données
  access {
    role          = "roles/bigquery.dataEditor"
    special_group = "projectWriters"
  }

  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }

  access {
    role          = "READER"
    special_group = "projectReaders"
  }

  labels = {
    environment = "production"
    managed_by  = "terraform"
    purpose     = "billing_export"
  }
}

# Permission pour le compte de service Cloud Billing
# Note: Le compte cloud-billing-export@system.gserviceaccount.com
# est créé automatiquement par Google lors de l'activation de l'export.
# Les permissions lui seront automatiquement accordées lors de la configuration
# de l'export dans la console GCP. Pas besoin de les gérer ici.

# ============================================================
# INSTRUCTIONS POUR ACTIVER L'EXPORT
# ============================================================
#
# Après avoir appliqué ce Terraform, activez l'export via :
#
# MÉTHODE 1 - Console GCP (recommandé) :
# 1. Aller sur https://console.cloud.google.com/billing
# 2. Sélectionner votre compte de facturation
# 3. Aller dans "Billing export" > "BigQuery export"
# 4. Cliquer "EDIT SETTINGS" pour "Detailed usage cost"
# 5. Sélectionner :
#    - Projet : onepiece-pipeline
#    - Dataset : billing_export
# 6. Sauvegarder
#
# MÉTHODE 2 - gcloud CLI :
#   Cette commande doit être exécutée avec un compte ayant
#   les permissions billing.accounts.update
#
#   gcloud billing projects link ${var.project_id} \
#     --billing-account=${var.billing_account_id}
#
#   Puis configurer l'export via l'API REST :
#   https://cloud.google.com/billing/docs/how-to/export-data-bigquery-setup
#
# VÉRIFICATION :
# Après activation, les données apparaîtront dans :
# - Table : billing_export.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX
# - Délai : ~24h pour les premières données
# - Format : Une ligne par SKU/service/jour
#
# REQUÊTE EXEMPLE pour voir vos coûts :
# SELECT
#   service.description AS service,
#   SUM(cost) AS total_cost,
#   currency
# FROM `onepiece-pipeline.billing_export.gcp_billing_export_v1_*`
# WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20241231'
# GROUP BY service, currency
# ORDER BY total_cost DESC
# ============================================================
