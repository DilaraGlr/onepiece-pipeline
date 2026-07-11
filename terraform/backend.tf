# Backend GCS pour stocker le state Terraform de manière sécurisée
# Le bucket t-lexicon-tfstate a été créé avec versioning activé
# pour permettre la récupération en cas d'erreur.

terraform {
  backend "gcs" {
    bucket = "t-lexicon-tfstate"
    prefix = "terraform/state"
  }
}
