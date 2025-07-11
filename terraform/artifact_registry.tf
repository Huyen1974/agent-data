resource "google_artifact_registry_repository" "agent_data_test_images" {
  project       = "github-chatgpt-ggcloud"
  location      = "asia-southeast1"
  repository_id = "agent-data-test-images" # Clear name for Test environment
  description   = "Repository for Agent Data TEST Docker images"
  format        = "DOCKER"
} 