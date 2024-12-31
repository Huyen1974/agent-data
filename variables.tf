variable "project_id" {
  type        = string
  description = "ID của dự án Google Cloud"
}

variable "region" {
  type        = string
  description = "Khu vực triển khai các tài nguyên Google Cloud"
  default     = "asia-southeast1"
}

variable "source_bucket_name" {
  type        = string
  description = "Tên bucket dùng để lưu mã nguồn cho Cloud Functions"
}

variable "function_source_object" {
  description = "Tên file mã nguồn đã nén (zip) để triển khai Cloud Functions"
  default     = "my-functions.zip"
}

variable "github_token" {
  type        = string
  description = "GitHub Token dùng để Terraform truy cập kho lưu trữ GitHub"
}

variable "service_account_email" {
  type        = string
  description = "Email của Service Account sử dụng trong Google Cloud"
}
