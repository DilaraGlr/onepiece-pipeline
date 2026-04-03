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

# ============================================================
# BIGQUERY
# ============================================================

resource "google_bigquery_dataset" "onepiece" {
  dataset_id = "onepiece"
  location   = "US"
}

resource "google_bigquery_table" "chapters" {
  dataset_id          = google_bigquery_dataset.onepiece.dataset_id
  table_id            = "chapters"
  deletion_protection = false

  schema = jsonencode([
    { name = "scraped_at",     type = "TIMESTAMP" },
    { name = "chapter_number", type = "INTEGER"   },
    { name = "source",         type = "STRING"    },
    { name = "language",       type = "STRING"    },
    { name = "url",            type = "STRING"    },
    { name = "image_count",    type = "INTEGER"   }
  ])
}

resource "google_bigquery_table" "dialogues" {
  dataset_id          = google_bigquery_dataset.onepiece.dataset_id
  table_id            = "dialogues"
  deletion_protection = false

  schema = jsonencode([
    { name = "chapter_number",  type = "INTEGER"   },
    { name = "page_number",     type = "INTEGER"   },
    { name = "image_url",       type = "STRING"    },
    { name = "gcs_path",        type = "STRING"    },
    { name = "extracted_text",  type = "STRING"    },
    { name = "processed_at",    type = "TIMESTAMP" }
  ])
}

resource "google_bigquery_table" "speakers" {
  dataset_id          = google_bigquery_dataset.onepiece.dataset_id
  table_id            = "speakers"
  deletion_protection = false

  schema = jsonencode([
    { name = "chapter_number", type = "INTEGER" },
    { name = "page_number",    type = "INTEGER" },
    { name = "speaker",        type = "STRING"  },
    { name = "phrase",         type = "STRING"  },
    { name = "luffy_says_it",  type = "BOOLEAN" },
    { name = "about_luffy",    type = "BOOLEAN" }
  ])
}

# ============================================================
# GOOGLE CLOUD STORAGE
# ============================================================

resource "google_storage_bucket" "manga_images" {
  name          = "onepiece-manga-images"
  location      = var.region
  force_destroy = false
}

# ============================================================
# SECRET MANAGER
# ============================================================

resource "google_secret_manager_secret" "anthropic_api_key" {
  secret_id = "anthropic-api-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }
}

# ============================================================
# ARTIFACT REGISTRY
# ============================================================

resource "google_artifact_registry_repository" "onepiece_repo" {
  location      = var.region
  repository_id = "onepiece-repo"
  format        = "DOCKER"
}

# ============================================================
# CLOUD RUN JOBS
# ============================================================

resource "google_cloud_run_v2_job" "scraper" {
  name     = "onepiece-scraper-job"
  location = var.region

  template {
    template {
      containers {
        image = "europe-west1-docker.pkg.dev/${var.project_id}/onepiece-repo/scraper:latest"

        env {
          name  = "CHAPTER_LIMIT"
          value = var.chapter_limit
        }

        env {
          name  = "PIPELINE_MODE"
          value = "scraper"
        }
      }
      timeout = "3600s"
    }
  }
}

resource "google_cloud_run_v2_job" "ocr" {
  name     = "ocr-pipeline-job"
  location = var.region

  template {
    template {
      containers {
        image = "europe-west1-docker.pkg.dev/${var.project_id}/onepiece-repo/scraper:latest"

        env {
          name  = "PIPELINE_MODE"
          value = "ocr"
        }
      }
      timeout = "86400s"
    }
  }
}

resource "google_cloud_run_v2_job" "nlp" {
  name     = "nlp-pipeline-job"
  location = var.region

  template {
    template {
      containers {
        image = "europe-west1-docker.pkg.dev/${var.project_id}/onepiece-repo/nlp-pipeline:latest"
      }
      timeout = "86400s"
    }
  }
}

# ============================================================
# CLOUD RUN SERVICE (Dashboard)
# ============================================================

resource "google_cloud_run_v2_service" "dashboard" {
  name     = "onepiece-dashboard"
  location = var.region

  template {
    containers {
      image = "europe-west1-docker.pkg.dev/${var.project_id}/onepiece-repo/dashboard:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          memory = "512Mi"
          cpu    = "1"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Permettre l'accès public au dashboard
resource "google_cloud_run_service_iam_member" "dashboard_public" {
  location = google_cloud_run_v2_service.dashboard.location
  service  = google_cloud_run_v2_service.dashboard.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ============================================================
# CLOUD SCHEDULER
# ============================================================

resource "google_cloud_scheduler_job" "weekly" {
  name     = "onepiece-scheduler"
  schedule = "0 9 * * 1"
  region   = var.region

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/workflows/onepiece-workflow/executions"

    oauth_token {
      service_account_email = "${var.project_number}-compute@developer.gserviceaccount.com"
    }
  }
}