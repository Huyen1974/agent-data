variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "service_account_email" {
  description = "The service account email"
  type        = string
}

# IAM roles for the service account
resource "google_project_iam_member" "service_account_roles" {
  for_each = toset([
    "roles/storage.admin",
    "roles/cloudfunctions.admin",
    "roles/run.admin",
    "roles/workflows.admin",
    "roles/artifactregistry.admin",
    "roles/logging.admin",
    "roles/monitoring.admin",
    "roles/datastore.user"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${var.service_account_email}"
}

data "google_project" "current" {
  project_id = var.project_id
}

output "service_account_email" {
  description = "The service account email"
  value       = var.service_account_email
} 