# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "agent_data_docker_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "agent-data-${var.environment}"
  description   = "Agent Data ${title(var.environment)} Docker Repository"
  format        = "DOCKER"

  labels = {
    environment = var.environment
    project     = "agent-data-langroid"
    managed_by  = "terraform"
  }
}
