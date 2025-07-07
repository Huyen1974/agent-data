resource "google_project_iam_member" "cloud_run_invoker_binding" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${var.service_account_email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "cloudfunctions_invoker_binding" {
  project = var.project_id
  role    = "roles/cloudfunctions.invoker"
  member  = "serviceAccount:${var.service_account_email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "pubsub_publisher_binding" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${var.service_account_email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "secret_accessor_binding" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${var.service_account_email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "storage_object_admin_binding" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${var.service_account_email}"

  lifecycle {
    prevent_destroy = true
  }
}

# Allow compute engine to use the service account for Cloud Run
resource "google_project_iam_member" "compute_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:service-${data.google_project.current.number}@compute-system.iam.gserviceaccount.com"

  lifecycle {
    prevent_destroy = true
  }
}

# Allow workflows service to act as the service account
resource "google_project_iam_member" "workflows_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:service-${data.google_project.current.number}@workflows-system.iam.gserviceaccount.com"

  lifecycle {
    prevent_destroy = true
  }
}

# Allow the project to impersonate the cross-project service account
resource "google_service_account_iam_member" "cross_project_token_creator" {
  service_account_id = "projects/github-chatgpt-ggcloud/serviceAccounts/${var.service_account_email}"
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@compute-system.iam.gserviceaccount.com"
}

resource "google_service_account_iam_member" "cross_project_user" {
  service_account_id = "projects/github-chatgpt-ggcloud/serviceAccounts/${var.service_account_email}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${data.google_project.current.number}@compute-system.iam.gserviceaccount.com"
}

resource "google_service_account_iam_member" "workflows_cross_project_user" {
  service_account_id = "projects/github-chatgpt-ggcloud/serviceAccounts/${var.service_account_email}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${data.google_project.current.number}@workflows-system.iam.gserviceaccount.com"
}

# Data source to get project information
data "google_project" "current" {
  project_id = var.project_id
}

# Cấp quyền đọc secrets từ nhánh Production
resource "google_project_iam_member" "secret_accessor_binding_prod" {
  project = "github-chatgpt-ggcloud" # Project chứa secrets
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${var.service_account_email}"

  lifecycle {
    prevent_destroy = true
  }
}
