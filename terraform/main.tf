terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_bigquery_dataset" "onepiece" {
  dataset_id = "onepiece"
  location   = "US"
}

resource "google_bigquery_table" "chapters" {
  dataset_id = google_bigquery_dataset.onepiece.dataset_id
  table_id   = "chapters"
  
  schema = jsonencode([
    { name = "scraped_at",     type = "TIMESTAMP" },
    { name = "chapter_number", type = "INTEGER"    },
    { name = "source",         type = "STRING"    },
    { name = "language",       type = "STRING"    },
    { name = "url",            type = "STRING"    },
    { name = "image_count",    type = "INTEGER"   }
  ])
}

resource "google_cloud_run_v2_job" "scraper" {
  name     = "onepiece-scraper-job"
  location = var.region

  template {
    template {
      containers {
        image = "europe-west1-docker.pkg.dev/${var.project_id}/onepiece-repo/onepiece-scraper:latest"
        
        env {
          name  = "CHAPTER_LIMIT"
          value = var.chapter_limit
        }
      }
      timeout = "3600s"
    }
  }
}

resource "google_cloud_scheduler_job" "weekly" {
  name     = "onepiece-scheduler"
  schedule = "0 9 * * 1"
  region   = var.region

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/workflows/onepiece-workflow/executions"
    
    oauth_token {
      service_account_email = "682150386282-compute@developer.gserviceaccount.com"
    }
  }
}