terraform {
  backend "gcs" {
    bucket = "huyen1974-agent-data-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "cloud_storage" {
  source                  = "./modules/cloud_storage"
  project_id              = var.project_id
  region                  = var.region
  function_storage_bucket = var.function_storage_bucket
  artifacts_bucket        = var.artifacts_bucket
  log_bucket              = var.log_bucket
}

module "firestore" {
  source     = "./modules/firestore"
  project_id = var.project_id
  region     = var.firestore_database_region
  name       = var.firestore_db_name
}

module "cloud_run" {
  service_name    = "agent-data-dummy-service"
  container_image = var.container_image
  source          = "./modules/cloud_run"
  project_id      = var.project_id
  region          = var.region
}

module "iam" {
  source                = "./modules/iam"
  project_id            = var.project_id
  service_account_email = var.service_account_email
}

data "google_secret_manager_secret_version" "github_token" {
  secret  = "github-token-sg"
  project = "github-chatgpt-ggcloud"
}

data "google_secret_manager_secret_version" "lark_access_token" {
  secret  = "lark-access-token-sg"
  project = "github-chatgpt-ggcloud"
}

data "google_secret_manager_secret_version" "openai_api_key" {
  secret  = "openai-api-key-sg"
  project = "github-chatgpt-ggcloud"
}

data "google_secret_manager_secret_version" "lark_app_secret" {
  secret  = "lark-app-secret-sg"
  project = "github-chatgpt-ggcloud"
}

module "workflows" {
  source                = "./modules/workflows"
  project_id            = var.project_id
  region                = var.region
  workflow_name         = "agent-data-workflow"
  service_account_email = var.service_account_email
}

output "storage_bucket" {
  value       = module.cloud_storage.function_storage_bucket_name
  description = "The bucket used for storing Cloud Functions"
}

output "service_account_email" {
  value       = var.service_account_email
  description = "Service account email"
}
