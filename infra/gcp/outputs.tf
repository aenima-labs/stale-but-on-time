output "instance" {
  value = google_compute_instance.runner.name
}

output "zone" {
  value = google_compute_instance.runner.zone
}

output "bucket" {
  value = google_storage_bucket.job.name
}
