variable "project_id" {
  description = "GCP project (Kodama's)"
  type        = string
  default     = "kodama-500509"
}

variable "region" {
  description = "Region (Kodama's; G4 is offered in europe-west1-b and -c)"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  type    = string
  default = "europe-west1-b"
}

variable "run_id" {
  description = "Short lowercase id for resource names (letters, digits, hyphens)"
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,19}$", var.run_id))
    error_message = "run_id: 2-20 characters, lowercase letters, digits and hyphens, starting with a letter."
  }
}

variable "run_name" {
  description = "The run's folder under results/ (written by the job)"
  type        = string
}

variable "run_args" {
  description = "Extra arguments for src/e2_run.py on the machine (e.g. --model gemma4:26b)"
  type        = string
  default     = ""
}

variable "machine_type" {
  description = "g4-standard-48 (1x RTX PRO 6000, 96 GB) or g2-standard-8/16 (1x L4, 24 GB)"
  type        = string
  default     = "g4-standard-48"
}

variable "spot" {
  description = "Spot provisioning (cheaper, can be preempted; the job then fails and is deleted)"
  type        = bool
  default     = false
}

variable "max_lifetime_hours" {
  description = "Hard lifetime: Compute Engine deletes the machine after this many hours"
  type        = number
  default     = 4
  validation {
    condition     = var.max_lifetime_hours >= 1 && var.max_lifetime_hours <= 12
    error_message = "max_lifetime_hours must be between 1 and 12."
  }
}

variable "image" {
  description = "Boot image with the NVIDIA driver (G4 needs R580 or later). Check with: gcloud compute images describe-from-family common-cu129-ubuntu-2404-nvidia-580 --project deeplearning-platform-release"
  type        = string
  default     = "projects/deeplearning-platform-release/global/images/family/common-cu129-ubuntu-2404-nvidia-580"
}

variable "disk_gib" {
  type    = number
  default = 200
}

variable "models" {
  description = "Ollama models pulled before the run"
  type        = list(string)
  default     = ["gemma4:e4b", "nomic-embed-text"]
}

variable "ollama_version" {
  description = "Ollama release (the stored runs used 0.40.13)"
  type        = string
  default     = "0.40.13"
}

variable "uv_version" {
  type    = string
  default = "0.13.6"
}

variable "source_tarball" {
  description = "git archive of the repository at the commit to run (written by the task)"
  type        = string
}

variable "allow_iap_ssh" {
  description = "Allow SSH through IAP for debugging"
  type        = bool
  default     = false
}
