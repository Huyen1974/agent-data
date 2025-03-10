resource "google_cloud_run_service" "default" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    spec {
      service_account_name = "gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com"  # Chỉ định service account
      containers {
        image = var.container_image
        ports {
          container_port = 8080
        }
        env {
          name  = "ENVIRONMENT"
          value = "test"
        }
        env {
          name = "GITHUB_TOKEN"
          value_from {
            secret_key_ref {
              name = "github-token-sg"
              key  = "latest"
            }
          }
        }
        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = "chatgpt-deployer-key"
              key  = "latest"
            }
          }
        }
        env {
          name = "LARK_ACCESS_TOKEN"
          value_from {
            secret_key_ref {
              name = "lark-access-token-sg"
              key  = "latest"
            }
          }
        }
        env {
          name = "LARK_APP_SECRET"
          value_from {
            secret_key_ref {
              name = "lark-app-secret-sg"
              key  = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    prevent_destroy = true  # Khôi phục để bảo vệ Cloud Run
    ignore_changes  = [
      template[0].spec[0].containers[0].image  # Bỏ qua thay đổi image do CI/CD quản lý
    ]
  }
}
