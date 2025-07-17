locals {
  bucket_purposes = toset([
    "source", "artifacts", "logs", "knowledge", "qdrant-snapshots", "tfstate"
  ])
}

# GCS buckets for different purposes
resource "google_storage_bucket" "agent_data_buckets" {
  for_each = local.bucket_purposes

  project       = var.project_id
  name          = "huyen1974-agent-data-${each.key}-${var.environment}"
  location      = var.region
  storage_class = "STANDARD"
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = var.environment
    project     = "agent-data-langroid"
    managed_by  = "terraform"
  }
}
