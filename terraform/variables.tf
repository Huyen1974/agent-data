variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "asia-southeast1"
}

variable "environment" {
  description = "Environment (test/production)"
  type        = string
  validation {
    condition     = contains(["test", "production"], var.environment)
    error_message = "Environment must be either 'test' or 'production'."
  }
} 