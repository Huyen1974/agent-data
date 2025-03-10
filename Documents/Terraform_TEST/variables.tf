variable "project_id" {
  description = "Google Cloud project ID for the test environment"
  type        = string
}

variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "asia-southeast1"
}

variable "terraform_state_bucket" {
  description = "The bucket name for Terraform state storage"
  type        = string
  default     = "huyen1974-my-terraform-test-state"
}

variable "artifacts_bucket" {
  description = "The bucket for storing artifacts"
  type        = string
  default     = "huyen1974-artifact-storage-test"
}

variable "log_bucket" {
  description = "The bucket for storing logs"
  type        = string
  default     = "huyen1974-log-storage-test"
}

variable "function_storage_bucket" {
  description = "The bucket for storing Cloud Functions code"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables for functions"
  type        = map(string)
  default     = {}
}

variable "service_account_email" {
  description = "Service account email for Google Cloud"
  type        = string
  default     = "gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com"
}

variable "firestore_database_region" {
  description = "Firestore database region"
  type        = string
  default     = "asia-southeast1"
}

variable "container_image" {
  description = "Image của container"
  type        = string
}

variable "firestore_db_name" {
  description = "Name of the Firestore database"
  type        = string
  default     = "(default)"
}
