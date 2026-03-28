variable "project_id" {
  description = "L'identifiant du projet Google Cloud"
  type        = string
  default     = "onepiece-pipeline"
}

variable "region" {
  description = "La région Google Cloud utilisée pour tous les services"
  type        = string
  default     = "europe-west1"
}

variable "chapter_limit" {
  description = "Nombre de chapitres à scraper"
  type        = string
  default     = "1172"
}