variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "service_account_email" {
  description = "The service account email for Cloud Run services"
  type        = string
}

variable "region" {
  description = "The region for Cloud Run services"
  type        = string
  default     = "asia-southeast1"
}

# Enable Cloud Run API
resource "google_project_service" "cloud_run" {
  project = var.project_id
  service = "run.googleapis.com"
  
  disable_dependent_services = false
  disable_on_destroy         = false
}

# Enable Artifact Registry API
resource "google_project_service" "artifact_registry" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"
  
  disable_dependent_services = false
  disable_on_destroy         = false
}

# Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "docker_repo" {
  repository_id = "docker-repo"
  location      = var.region
  format        = "DOCKER"
  project       = var.project_id
  
  description = "Docker repository for agent-data containers"
  
  depends_on = [google_project_service.artifact_registry]
}

# Additional Artifact Registry repository for agent-data
resource "google_artifact_registry_repository" "agent_data_repo" {
  repository_id = "agent-data"
  location      = var.region
  format        = "DOCKER"
  project       = var.project_id
  
  description = "Docker repository for agent-data project"
  
  depends_on = [google_project_service.artifact_registry]
}

output "artifact_registry_url" {
  description = "The Artifact Registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/docker-repo"
}

output "agent_data_registry_url" {
  description = "The Agent Data Artifact Registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/agent-data"
} 