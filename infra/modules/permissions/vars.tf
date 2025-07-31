# Project ID passed down from ../variables.tf
variable "project_id" {
    type = string
}

# The list of project level roles for hyggeskyen SA
# Passed down from ../variables.tf
variable "project_level_roles" {
  type = list(object({
    role = string
  }))
}