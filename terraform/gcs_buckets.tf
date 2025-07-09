locals {
  environment = terraform.workspace == "production" ? "production" : "test"
  bucket_purposes = toset([
    "source", "artifacts", "logs", "knowledge", "qdrant-snapshots"
  ])
}

resource "google_storage_bucket" "env_buckets" {
  for_each = local.bucket_purposes
  project  = "github-chatgpt-ggcloud"
  name     = "huyen1974-agent-data-${each.key}-${local.environment}"
  location = "asia-southeast1"
  storage_class = "STANDARD"
  force_destroy = true
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
}

resource "google_storage_bucket" "terraform_state_test" {
  provider = google
  project  = "github-chatgpt-ggcloud"
  name     = "huyen1974-agent-data-tfstate-test"
  location = "asia-southeast1"
  storage_class = "STANDARD"
  force_destroy = true
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
} 