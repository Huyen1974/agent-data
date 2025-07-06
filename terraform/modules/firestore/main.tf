variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "firestore_db_name" {
  description = "The Firestore database name"
  type        = string
  default     = "(default)"
}

variable "region" {
  description = "The region for Firestore"
  type        = string
  default     = "asia-southeast1"
}

# Enable Firestore API
resource "google_project_service" "firestore" {
  project = var.project_id
  service = "firestore.googleapis.com"
  
  disable_dependent_services = false
  disable_on_destroy         = false
}

output "firestore_service_enabled" {
  description = "Whether Firestore API is enabled"
  value       = google_project_service.firestore.service
} 