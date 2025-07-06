module "firestore" {
  source = "./modules/firestore"
  project_id = "chatgpt-db-project"
  firestore_db_name = "(default)"
  region = "asia-southeast1"
}

module "buckets" {
  source = "./modules/storage"
  project_id = "chatgpt-db-project"
  buckets = [
    "huyen1974-agent-data-terraform-state",
    "huyen1974-faiss-index-storage-test",
    "huyen1974-artifact-storage-test",
    "huyen1974-log-storage-test"
  ]
}

module "cloud_run" {
  source = "./modules/cloud_run"
  project_id = "chatgpt-db-project"
  service_account_email = "gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com"
}

module "workflows" {
  source = "./modules/workflows"
  project_id = "chatgpt-db-project"
  workflow_name = "my-workflow-test"
}

module "iam" {
  source = "./modules/iam"
  project_id = "chatgpt-db-project"
  service_account_email = "gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com"
} 