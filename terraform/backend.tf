terraform {
  backend "gcs" {
    bucket = "onepiece-tfstate"
    prefix = "terraform/state"
  }
}
