variable "project_id" {
    type = string
}

variable "region" {
    type    = string
    default = "europe-west1"
}

variable "resource_prefix" {
    type = string
    default = "myldretid-kbh"
}

# List of the required project level roles for the hyggeskyen SA 
variable "project_level_roles" {
  type = list(object({
    role = string
  }))
  default = [
    { role = "roles/storage.objectAdmin" },
    { role = "roles/storage.objectViewer" },
    { role = "roles/pubsub.subscriber" },
    { role = "roles/logging.logWriter" },
    { role = "roles/run.invoker" }
  ]
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