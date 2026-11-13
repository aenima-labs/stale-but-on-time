# One Experiment 2 run on a GPU machine in GCP: a machine with Ollama and the
# models on it runs the experiment, writes the results to a bucket and deletes
# itself. Started and torn down by `uv run inv gcp.run` (tasks/gcp.py); see
# README.md in this folder.
#
# Conventions follow Kodama's infra/terraform: project kodama-500509, region
# europe-west1, one service account per job, APIs enabled by Kodama's
# configuration (compute, iam, storage), which this module does not manage.
#
# Three independent stops, so a hung run cannot keep billing:
#   1. the job's startup script deletes the machine when it ends, success or not;
#   2. Compute Engine deletes the machine at max_run_duration (hard lifetime);
#   3. the Invoke task runs `terraform destroy` in a finally block, and on timeout.

terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # Local state: the job is short-lived and the task destroys everything it
  # created. State lives in infra/gcp/terraform.tfstate (gitignored).
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}

locals {
  name     = "sbot-e2-${var.run_id}"
  # G4 machines take Hyperdisk only; G2 takes Persistent Disk.
  disk_type = startswith(var.machine_type, "g4-") ? "hyperdisk-balanced" : "pd-balanced"
  labels = {
    purpose = "stale-but-on-time"
    job     = "e2-gcp-run"
    run     = var.run_id
  }
}

# ---------------------------------------------------------------- storage ---

# Results and the source tarball. Deleted with the job (force_destroy) after
# the task has copied the results back; objects expire after 14 days anyway.
resource "google_storage_bucket" "job" {
  name                        = "${var.project_id}-${local.name}"
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
  labels                      = local.labels

  lifecycle_rule {
    condition {
      age = 14
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket_object" "source" {
  name   = "source/${basename(var.source_tarball)}"
  bucket = google_storage_bucket.job.name
  source = var.source_tarball
}

# ------------------------------------------------------- service account ---

resource "google_service_account" "runner" {
  account_id   = "sbot-e2-${substr(var.run_id, 0, 20)}"
  display_name = "Stale but on Time E2 runner (${var.run_id})"
}

resource "google_storage_bucket_iam_member" "runner_objects" {
  bucket = google_storage_bucket.job.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runner.email}"
}

# The machine may delete itself and nothing else.
resource "google_project_iam_member" "runner_self_delete" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.runner.email}"
  condition {
    title      = "only-${local.name}"
    expression = "resource.name == \"projects/${var.project_id}/zones/${var.zone}/instances/${local.name}\""
  }
}

# ---------------------------------------------------------------- network ---

resource "google_compute_network" "job" {
  name                    = local.name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "job" {
  name          = local.name
  network       = google_compute_network.job.id
  region        = var.region
  ip_cidr_range = "10.80.0.0/24"
}

# No ingress except SSH through Identity-Aware Proxy, and only if asked for.
resource "google_compute_firewall" "iap_ssh" {
  count         = var.allow_iap_ssh ? 1 : 0
  name          = "${local.name}-iap-ssh"
  network       = google_compute_network.job.id
  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

# ---------------------------------------------------------------- machine ---

resource "google_compute_instance" "runner" {
  name         = local.name
  zone         = var.zone
  machine_type = var.machine_type
  labels       = local.labels

  boot_disk {
    auto_delete = true
    initialize_params {
      image = var.image
      size  = var.disk_gib
      type  = local.disk_type
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.job.id
    # An ephemeral public address for egress (Ollama, models, Python packages).
    # No ingress rule allows anything in.
    access_config {}
  }

  scheduling {
    on_host_maintenance         = "TERMINATE" # required for GPUs
    automatic_restart           = false
    provisioning_model          = var.spot ? "SPOT" : "STANDARD"
    preemptible                 = var.spot
    instance_termination_action = "DELETE"
    # Hard lifetime: Compute Engine deletes the machine at this point, whatever
    # the job is doing.
    max_run_duration {
      seconds = var.max_lifetime_hours * 3600
    }
  }

  service_account {
    email  = google_service_account.runner.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin = "TRUE"
    startup-script = templatefile("${path.module}/startup.sh.tftpl", {
      bucket         = google_storage_bucket.job.name
      source_object  = google_storage_bucket_object.source.name
      run_name       = var.run_name
      instance       = local.name
      zone           = var.zone
      models         = join(" ", var.models)
      run_args       = var.run_args
      ollama_version = var.ollama_version
      uv_version     = var.uv_version
    })
  }

  depends_on = [
    google_storage_bucket_iam_member.runner_objects,
    google_project_iam_member.runner_self_delete,
  ]
}
