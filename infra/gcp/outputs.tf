output "bucket" {
  value = google_storage_bucket.data.name
}

output "registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "job" {
  value = google_cloud_run_v2_job.e2.name
}
