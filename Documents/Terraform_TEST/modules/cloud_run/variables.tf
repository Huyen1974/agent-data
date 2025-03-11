variable "project_id" {
  type        = string
  description = "Project ID"
}

variable "region" {
  type        = string
  description = "Region"
}

variable "service_name" {
  type        = string
  description = "Tên Cloud Run service"
}

variable "container_image" {
  type        = string
  description = "Container image để deploy"
}
