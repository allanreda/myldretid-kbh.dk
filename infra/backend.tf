terraform {
  backend "gcs" {
    bucket  = "myldretid-kbh-terraform-backend"
    prefix  = "terraform/state"
  }
}
