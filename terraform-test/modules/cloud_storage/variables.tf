variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
}

variable "artifacts_bucket" {
  type        = string
  description = "Tên bucket artifact"
}

variable "function_storage_bucket" {
  type        = string
  description = "Tên bucket code Cloud Functions"
}

variable "log_bucket" {
  type        = string
  description = "Tên bucket logs"
}
