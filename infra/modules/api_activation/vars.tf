# Project ID passed down from ../variables.tf
variable "project_id" {
    type = string
}

# List of the required APIs to enable
variable "api_list" {
  type = list(string)
  default = [
    "run.googleapis.com",             # Cloud Run
    "cloudscheduler.googleapis.com",  # Cloud Scheduler
    "pubsub.googleapis.com",          # Pub/Sub
    "storage.googleapis.com",         # Cloud Storage
    "logging.googleapis.com",         # Logging
  ]
}