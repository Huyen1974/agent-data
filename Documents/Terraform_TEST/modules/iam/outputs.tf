output "cloud_run_invoker_binding" {
  value       = google_project_iam_member.cloud_run_invoker_binding.member
  description = "Cloud Run Invoker IAM Binding"
}

output "cloudfunctions_invoker_binding" {
  value       = google_project_iam_member.cloudfunctions_invoker_binding.member
  description = "Cloud Functions Invoker IAM Binding"
}

output "secret_accessor_binding" {
  value       = google_project_iam_member.secret_accessor_binding.member
  description = "Secret Manager Access IAM Binding"
}
