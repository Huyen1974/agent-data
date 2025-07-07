output "artifact_storage_bucket_name" {
  value       = google_storage_bucket.artifact_storage.name
  description = "Tên bucket artifact"
}

output "log_storage_bucket_name" {
  value       = google_storage_bucket.log_storage.name
  description = "Tên bucket logs"
}

output "function_storage_bucket_name" {
  value       = google_storage_bucket.function_storage.name
  description = "Tên bucket code Cloud Functions"
}
