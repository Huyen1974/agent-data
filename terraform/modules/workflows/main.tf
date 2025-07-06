variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "workflow_name" {
  description = "The name of the workflow"
  type        = string
}

variable "region" {
  description = "The region for Cloud Workflows"
  type        = string
  default     = "asia-southeast1"
}

# Enable Cloud Workflows API
resource "google_project_service" "workflows" {
  project = var.project_id
  service = "workflows.googleapis.com"
  
  disable_dependent_services = false
  disable_on_destroy         = false
}

# Enable Cloud Functions API (often used with workflows)
resource "google_project_service" "cloudfunctions" {
  project = var.project_id
  service = "cloudfunctions.googleapis.com"
  
  disable_dependent_services = false
  disable_on_destroy         = false
}

output "workflows_enabled" {
  description = "Whether Cloud Workflows API is enabled"
  value       = google_project_service.workflows.service
}

output "cloudfunctions_enabled" {
  description = "Whether Cloud Functions API is enabled"  
  value       = google_project_service.cloudfunctions.service
} 