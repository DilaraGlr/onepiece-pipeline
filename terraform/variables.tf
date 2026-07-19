variable "project_id" {
  description = "L'identifiant du projet Google Cloud"
  type        = string
  default     = "t-lexicon-231513"
}

variable "project_number" {
  description = "Le numéro du projet Google Cloud"
  type        = string
  default     = "991582752931"
}

variable "region" {
  description = "La région Google Cloud utilisée pour tous les services"
  type        = string
  default     = "europe-west1"
}

variable "chapter_limit" {
  description = "Nombre de chapitres à scraper (0 = tous)"
  type        = string
  default     = "3"
}

variable "image_tag" {
  description = "Tag Docker des images (hash Git ou 'latest')"
  type        = string
  default     = "latest"
}

variable "billing_account_id" {
  description = "ID du compte de facturation Google Cloud (format: 012345-6789AB-CDEF01)"
  type        = string
  # Pas de default : cette valeur ne doit jamais être commitée dans Git
  # Définissez-la dans terraform/terraform.tfvars (voir terraform.tfvars.example)
  # Trouvez votre Billing Account ID :
  # - Console: https://console.cloud.google.com/billing
  # - CLI: gcloud billing accounts list
}

variable "monthly_budget_amount" {
  description = "Montant du budget mensuel en EUR (ou USD selon votre devise)"
  type        = string
  default     = "50"  # 50 EUR par défaut - ajustez selon vos besoins
}