# Project ID passed down from ../variables.tf
variable "project_id" {}

# The list of required APIs
# Passed down from ../variables.tf
variable "api_list" {
  type = list(string)
}