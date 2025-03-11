output "cloud_run_service_name" {
  value       = google_cloud_run_service.default.name
  description = "Tên Cloud Run service"
}

output "cloud_run_service_url" {
  value       = google_cloud_run_service.default.status[0].url
  description = "URL của Cloud Run service"
}