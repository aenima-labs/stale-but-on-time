variable "project_id" {
  description = "GCP project (Kodama's)"
  type        = string
  default     = "kodama-500509"
}

variable "region" {
  description = "Region (Kodama's). Cloud Run jobs offer the NVIDIA L4 here; the RTX PRO 6000 is not offered in europe-west1."
  type        = string
  default     = "europe-west1"
}

variable "image" {
  description = "Job image (pushed by the task, tagged with the commit). A public placeholder until the first build."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/job:latest"
}

variable "gpu" {
  description = "Cloud Run GPU type: nvidia-l4 (or nvidia-rtx-pro-6000 where offered)"
  type        = string
  default     = "nvidia-l4"
}

variable "cpu" {
  description = "vCPUs (an L4 needs at least 4)"
  type        = number
  default     = 4
}

variable "memory_gib" {
  description = "Memory in GiB (an L4 needs at least 16). The container file system is in memory, and the models (~10 GB) are copied into it."
  type        = number
  default     = 24
}

variable "task_timeout_hours" {
  description = "Hard limit on one execution; Cloud Run stops the task here (at most 12 with a GPU)"
  type        = number
  default     = 2
  validation {
    condition     = var.task_timeout_hours >= 1 && var.task_timeout_hours <= 12
    error_message = "task_timeout_hours must be between 1 and 12."
  }
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete the bucket with its models and results"
  type        = bool
  default     = false
}
