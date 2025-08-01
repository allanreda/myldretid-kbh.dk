variable "project_id" {
    type = string
}

variable "region" {
    type    = string
    default = "europe-west1"
}

variable "service_account_email" {
    type = string
    default = "myldretid-kbh@sylvan-mode-413619.iam.gserviceaccount.com"
}

variable "domain" {
    type    = string
    default = "http://myldretid-kbh.dk"
}

