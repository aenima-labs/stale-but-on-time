# Experiment 2 as a Cloud Run job with a GPU. Started by `uv run inv gcp.run`
# (src/gcp_job.py); see README.md in this folder.
#
# Conventions follow Kodama's infra/terraform (project kodama-500509, region
# europe-west1, images in an Artifact Registry repository, a service account per
# job, Cloud Run v2 jobs with max_retries 0), but this is its own configuration
# with its own state: nothing in Kodama's Terraform is read or changed. The APIs
# (run, artifactregistry, storage, iam) are enabled by Kodama's configuration.
#
# Nothing here bills while idle except storage: the image in Artifact Registry
# and the models and results in the bucket. A job execution bills per second
# while it runs and is killed at the task timeout (at most 12 h with a GPU).

terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # Local state (infra/gcp/terraform.tfstate, gitignored).
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}

locals {
  name   = "stale-but-on-time"
  labels = { purpose = "stale-but-on-time" }
}

resource "google_artifact_registry_repository" "images" {
  repository_id = local.name
  location      = var.region
  format        = "DOCKER"
  description   = "Experiment images for the Stale but on Time paper"
  labels        = local.labels

  # Keep the five newest images; older ones are deleted.
  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }
  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      older_than = "2592000s"
    }
  }
}

# Models (the exact Ollama blobs of the local runs) under models/, and each
# run's results under results/<run>/.
resource "google_storage_bucket" "data" {
  name                        = "${var.project_id}-${local.name}"
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = var.force_destroy
  labels                      = local.labels
}

resource "google_service_account" "job" {
  account_id   = "sbot-e2-job"
  display_name = "Stale but on Time Experiment 2 job"
}

resource "google_storage_bucket_iam_member" "job_data" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.job.email}"
}

resource "google_cloud_run_v2_job" "e2" {
  name                = "sbot-e2"
  location            = var.region
  deletion_protection = false
  labels              = local.labels
  # GPU jobs longer than one hour are a Beta feature of Cloud Run.
  launch_stage = var.task_timeout_hours > 1 ? "BETA" : "GA"

  template {
    task_count = 1
    template {
      service_account = google_service_account.job.email
      max_retries     = 0
      timeout         = "${var.task_timeout_hours * 3600}s"
      # Jobs with a GPU run without zonal redundancy.
      gpu_zonal_redundancy_disabled = true

      node_selector {
        accelerator = var.gpu
      }

      containers {
        image = var.image

        resources {
          limits = {
            cpu              = tostring(var.cpu)
            memory           = "${var.memory_gib}Gi"
            "nvidia.com/gpu" = "1"
          }
        }

        # Overridden per execution by the task (gcloud run jobs execute --update-env-vars).
        env {
          name  = "RUN_NAME"
          value = "unset"
        }
        env {
          name  = "RUN_ARGS"
          value = ""
        }

        volume_mounts {
          name       = "data"
          mount_path = "/gcs"
        }
      }

      volumes {
        name = "data"
        gcs {
          bucket    = google_storage_bucket.data.name
          read_only = false
        }
      }
    }
  }

  depends_on = [google_storage_bucket_iam_member.job_data]
}
