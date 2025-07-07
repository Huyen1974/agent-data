variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "service_account_email" {
  description = "The email of the service account"
  type        = string
  default     = "chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com"
}
