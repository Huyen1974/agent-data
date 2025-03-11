variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Region cho Workflows"
  type        = string
}

variable "workflow_name" {
  description = "Tên Workflow"
  type        = string
}

variable "service_account_email" {
  description = "Service Account email để chạy workflow"
  type        = string
}
