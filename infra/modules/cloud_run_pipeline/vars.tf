# Passed down from ../variables.tf
variable "project_id" {
    type = string
}
# Passed down from ../variables.tf
variable "region" {
    type = string
}

# Passed down from ../variables.tf
variable "service_account_email" {
    type = string
}

variable "name" {
  type = string
}

variable "image" {
  type = string
}

variable "cpu" {
  type = number
}

variable "memory" {
  type = string
}

variable "schedule" {
  type = string
}