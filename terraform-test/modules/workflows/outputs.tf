output "workflow_name" {
  value       = google_workflows_workflow.default.name
  description = "The name of the Workflow"
}

output "workflow_service_account" {
  value       = google_workflows_workflow.default.service_account
  description = "The service account associated with the Workflow"
}
