variable "project_id" {
    type = string
}

variable "external_project_id" {
    type = string
}

variable "region" {
    type    = string
    default = "europe-west1"
}

variable "service_account_name" {
    type = string
}

variable "service_account_email" {
    type = string
}

variable "domain" {
    type    = string
    default = "http://myldretid-kbh.dk"
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
    "iam.googleapis.com"
  ]
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