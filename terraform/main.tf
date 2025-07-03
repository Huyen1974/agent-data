terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "huyen1974-agent-data-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = "github-chatgpt-ggcloud"
  region  = "asia-southeast1"
}

# FAISS Index Storage Bucket
resource "google_storage_bucket" "faiss_index_storage" {
  name     = "huyen1974-faiss-index-storage-test"
  location = "ASIA-SOUTHEAST1"
  project  = "github-chatgpt-ggcloud"

  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = "test"
    purpose     = "faiss-index-storage"
    managed_by  = "terraform"
  }
}

# Qdrant Snapshots Bucket
resource "google_storage_bucket" "qdrant_snapshots" {
  name     = "huyen1974-qdrant-snapshots"
  location = "ASIA-SOUTHEAST1"
  project  = "github-chatgpt-ggcloud"

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
    environment = "production"
    purpose     = "qdrant-snapshots"
    managed_by  = "terraform"
  }
}

# Terraform State Bucket
resource "google_storage_bucket" "terraform_state" {
  name     = "huyen1974-agent-data-terraform-state"
  location = "ASIA-SOUTHEAST1"
  project  = "github-chatgpt-ggcloud"

  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = "infrastructure"
    purpose     = "terraform-state"
    managed_by  = "terraform"
  }
}

# Outputs
output "faiss_bucket_name" {
  description = "Name of the FAISS index storage bucket"
  value       = google_storage_bucket.faiss_index_storage.name
}

output "qdrant_bucket_name" {
  description = "Name of the Qdrant snapshots bucket"
  value       = google_storage_bucket.qdrant_snapshots.name
}

output "terraform_state_bucket_name" {
  description = "Name of the Terraform state bucket"
  value       = google_storage_bucket.terraform_state.name
} 