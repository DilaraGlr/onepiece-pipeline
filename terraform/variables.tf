variable "project_id" {
  description = "L'identifiant du projet Google Cloud"
  type        = string
  default     = "onepiece-pipeline"
}

variable "project_number" {
  description = "Le numéro du projet Google Cloud"
  type        = string
  default     = "682150386282"
}

variable "region" {
  description = "La région Google Cloud utilisée pour tous les services"
  type        = string
  default     = "europe-west1"
}

variable "chapter_limit" {
  description = "Nombre de chapitres à scraper (0 = tous)"
  type        = string
  default     = "0"
}

variable "image_tag" {
  description = "Tag Docker des images (hash Git ou 'latest')"
  type        = string
  default     = "latest"
}

variable "billing_account_id" {
  description = "ID du compte de facturation Google Cloud (format: 012345-6789AB-CDEF01)"
  type        = string
  # Trouvez votre Billing Account ID ici :
  # https://console.cloud.google.com/billing
  # Ou via CLI : gcloud billing accounts list
}

variable "monthly_budget_amount" {
  description = "Montant du budget mensuel en EUR (ou USD selon votre devise)"
  type        = string
  default     = "50"  # 50 EUR par défaut - ajustez selon vos besoins
}