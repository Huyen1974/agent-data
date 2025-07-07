resource "google_workflows_workflow" "default" {
  name            = var.workflow_name
  project         = var.project_id
  region          = var.region  # Sửa từ location thành region
  service_account = var.service_account_email

  source_contents = <<-EOT
    main:
      steps:
        - init:
            assign:
              - message: "Hello from Workflows (test)!"
        - log:
            call: sys.log
            args:
              text: $${message}
        - return:
            return: $${message}
  EOT

  lifecycle {
    prevent_destroy = true
  }
}
