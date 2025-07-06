terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    bucket = "huyen1974-agent-data-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = "chatgpt-db-project"
  region  = "asia-southeast1"
} 