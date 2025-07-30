terraform {
  backend "gcs" {
    bucket  = "myldretid-kbh-terraform-backend"
    prefix  = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}