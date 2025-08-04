# Project ID passed down from ../variables.tf
variable "project_id" {
    type = string
}

variable "external_project_id" {
    type = string
}


# SA name passed down from ../variables.tf
variable "service_account_name" {
    type = string
}

# Passed down from ../variables.tf
variable "cicd_service_account_email" {
    type = string
}

# The list of project level roles for deployment_sa 
# Passed down from ../variables.tf
variable "project_level_roles" {
  type = list(object({
    role = string
  }))
}

# The list of project level roles for cicd_sa 
# Passed down from ../variables.tf
variable "cicd_project_level_roles" {
  type = list(object({
    role = string
  }))
}