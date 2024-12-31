terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.57.0"
    }
  }
}

# Sử dụng bucket để lưu trữ log
resource "google_storage_bucket" "log_bucket" {
  name     = "terraform-log-bucket-${var.project_id}"
  location = var.region
}

# Cấu hình Logging Sink để chuyển log Terraform
resource "google_logging_project_sink" "terraform_log_sink" {
  name        = "terraform-log-sink"
  destination = "storage.googleapis.com/${google_storage_bucket.log_bucket.name}"
  filter      = "resource.type=\"cloud_function\""
}

# Gán quyền IAM cho Logging Sink
resource "google_project_iam_member" "log_sink_writer" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:github-chatgpt-ggcloud@appspot.gserviceaccount.com"
}

# Tạo Workflow cho CI/CD
resource "google_workflows_workflow" "ci_cd_workflow" {
  name        = "ci-cd-workflow"
  region      = var.region
  description = "A workflow to orchestrate CI/CD tasks"

  service_account = var.service_account_email

  source_contents = <<-EOT
    main:
      steps:
        - log_step:
            call: sys.log
            args:
              text: "Workflow started with updated configuration."
        - call_function:
            call: http.get
            args:
              url: "https://${google_cloudfunctions_function.ci_cd_function.https_trigger_url}"
        - return_step:
            return: "Workflow completed successfully."
  EOT
}

# Tạo Cloud Function
resource "google_cloudfunctions_function" "ci_cd_function" {
  name        = "ci-cd-function"
  runtime     = "python310"
  entry_point = "hello_http"
  region      = var.region

  source_archive_bucket = google_storage_bucket.log_bucket.name
  source_archive_object = "function-source.zip"

  trigger_http = true

  environment_variables = {
    FIRESTORE_PROJECT_ID = var.project_id
  }

  timeout = 60
}
