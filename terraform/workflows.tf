# ============================================================
# GOOGLE CLOUD WORKFLOWS
# ============================================================

# Workflow pour orchestrer l'exécution séquentielle des 3 pipelines
# 1. Scraper → Télécharge les chapitres
# 2. OCR → Extrait le texte des images
# 3. NLP → Analyse les dialogues et identifie les personnages

resource "google_workflows_workflow" "onepiece" {
  name            = "onepiece-workflow"
  region          = var.region
  description     = "Orchestre l'execution sequentielle: Scraper -> OCR -> NLP"

  # Service account dédié pour le workflow
  # Permissions: run.invoker (lancer les jobs) + run.viewer (voir leur statut)
  service_account = google_service_account.workflow.email

  # Utilise le fichier workflow.yaml existant dans scraper/
  # Ce fichier contient la logique d'orchestration déjà testée
  # qui lance séquentiellement : Scraper → OCR → NLP
  # avec vérification du statut toutes les 30 secondes
  source_contents = file("${path.module}/../scraper/workflow.yaml")

  # Dépendances: Le workflow doit attendre que les service accounts et les jobs existent
  depends_on = [
    google_service_account.workflow,
    google_cloud_run_v2_job.scraper,
    google_cloud_run_v2_job.ocr,
    google_cloud_run_v2_job.nlp,
    google_project_iam_member.workflow_run_invoker
  ]
}

# ============================================================
# OUTPUTS - Informations sur le workflow
# ============================================================

output "workflow_name" {
  description = "Nom du workflow"
  value       = google_workflows_workflow.onepiece.name
}

output "workflow_url" {
  description = "URL pour déclencher le workflow manuellement"
  value       = "https://console.cloud.google.com/workflows/workflow/${var.region}/${google_workflows_workflow.onepiece.name}?project=${var.project_id}"
}
