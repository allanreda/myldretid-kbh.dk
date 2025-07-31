# Project ID passed down from ../variables.tf
variable "project_id" {
    type = string
}
# Website domain passed down from ../variables.tf
variable "domain" {
    type = string
    default = null

}

# Name of the bucket
variable "name" {
  type = string
}

variable "region" {
    type = string
    default = "europe-west1"
}

variable "enable_cors" {
  type = bool
  default = false
}

variable "make_public" {
  description = "Whether to make the bucket publicly readable"
  type = bool
  default = false
}
