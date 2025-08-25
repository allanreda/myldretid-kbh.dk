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

variable "cicd_service_account_email" {
    type = string
}

variable "domains" {
  type = list(string)
}

variable "custom_domain_name" {
    type = string
}

variable "dns_ip" {
    type = string
}

variable "txt_value" {
    type = string
}

variable "search_console_verification_token" {
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
    "iam.googleapis.com",             # IAM
    "dns.googleapis.com"             # Cloud DNS
  ]
}

# List of the required project level roles for the deployment_sa 
variable "project_level_roles" {
  type = list(object({
    role = string
  }))
  default = [
    { role = "roles/storage.objectAdmin" },
    { role = "roles/storage.objectViewer" },
    { role = "roles/pubsub.subscriber" },
    { role = "roles/logging.logWriter" },
    { role = "roles/run.invoker" },
    { role = "roles/bigquery.user" },
    { role = "roles/dns.admin" }
  ]
}

# List of the required project level roles for the cicd_sa
variable "cicd_project_level_roles" {
  type = list(object({
    role = string
  }))
  default = [
    { role = "roles/artifactregistry.writer" },
    { role = "roles/run.admin" },
    { role = "roles/iam.serviceAccountUser" }
  ]
}