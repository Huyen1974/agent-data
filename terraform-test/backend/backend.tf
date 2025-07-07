terraform {
  backend "gcs" {
    bucket = "huyen1974-agent-data-terraform-state"
    prefix = "terraform/state"
  }
}
