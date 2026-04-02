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