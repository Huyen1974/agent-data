variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for IAM roles"
  type        = string
  default     = "gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com"
}
