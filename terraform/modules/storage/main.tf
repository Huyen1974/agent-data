variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "buckets" {
  description = "List of bucket names to create"
  type        = list(string)
}

variable "location" {
  description = "The location for the buckets"
  type        = string
  default     = "asia-southeast1"
}

resource "google_storage_bucket" "buckets" {
  for_each = toset(var.buckets)
  
  name          = each.value
  location      = var.location
  project       = var.project_id
  force_destroy = false
  
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
    environment = "test"
    managed_by  = "terraform"
    project     = "agent-data"
  }
}

output "bucket_names" {
  description = "Names of created buckets"
  value       = [for bucket in google_storage_bucket.buckets : bucket.name]
}

output "bucket_urls" {
  description = "URLs of created buckets"
  value       = [for bucket in google_storage_bucket.buckets : bucket.url]
} 