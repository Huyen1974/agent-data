output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "environment" {
  description = "The environment"
  value       = var.environment
}

output "gcs_buckets" {
  description = "Map of GCS bucket purposes to their names"
  value = {
    for purpose, bucket in google_storage_bucket.agent_data_buckets : 
    purpose => bucket.name
  }
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository details"
  value = {
    name     = google_artifact_registry_repository.agent_data_docker_repo.name
    location = google_artifact_registry_repository.agent_data_docker_repo.location
    id       = google_artifact_registry_repository.agent_data_docker_repo.repository_id
  }
} 