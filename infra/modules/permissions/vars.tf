# Project ID passed down from ../variables.tf
variable "project_id" {}

# The list of two project level roles
# Passed down from ../variables.tf
variable "project_level_roles" {
  type = list(object({
    role = string
  }))
}