# Project ID passed down from ../variables.tf
variable "project_id" {
    type = string
}

# SA email passed down from ../variables.tf
variable "service_account_email" {
    type = string
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