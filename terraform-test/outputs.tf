output "artifact_storage_bucket_name" {
  value       = module.cloud_storage.artifact_storage_bucket_name
  description = "The name of the artifact storage bucket"
}

output "log_storage_bucket_name" {
  value       = module.cloud_storage.log_storage_bucket_name
  description = "The name of the log storage bucket"
}

output "function_storage_bucket_name" {
  value       = module.cloud_storage.function_storage_bucket_name
  description = "The name of the function storage bucket"
}

output "firestore_database_region" {
  value       = var.firestore_database_region
  description = "Firestore database region"
}