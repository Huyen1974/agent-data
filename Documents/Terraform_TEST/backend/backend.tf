terraform {
  backend "gcs" {
    bucket = "huyen1974-my-terraform-test-state"
    prefix = "terraform-test/state"
  }
}
