
resource "google_dns_managed_zone" "myldretid-kbh-zone" {
  name = "myldretid-kbh-zone"
  dns_name = "${var.custom_domain_name}."
  project = var.project_id
  dnssec_config {
    state = "on"
    default_key_specs {
      algorithm  = "rsasha256"
      key_type   = "keySigning"
      key_length = 2048
    }
    default_key_specs {
      algorithm  = "rsasha256"
      key_type   = "zoneSigning"
      key_length = 1024
    }
  }
}

resource "google_dns_record_set" "firebase_a_record" {
  name         = "${var.custom_domain_name}."
  type         = "A"
  ttl          = 300
  project = var.project_id
  managed_zone = google_dns_managed_zone.myldretid-kbh-zone.name

  rrdatas = [var.dns_ip]
}

resource "google_dns_record_set" "txt_verification" {
  name         = "${var.custom_domain_name}."
  type         = "TXT"
  ttl          = 300
  project = var.project_id
  managed_zone = google_dns_managed_zone.myldretid-kbh-zone.name

  rrdatas = ["${var.txt_value}", 
            "${var.search_console_verification_token}"
        ]
}

# resource "google_dns_record_set" "search_console_verification" {
#   name         = "${var.custom_domain_name}."
#   type         = "TXT"
#   ttl          = 300
#   project = var.project_id
#   managed_zone = google_dns_managed_zone.myldretid-kbh-zone.name

#   rrdatas = ["${var.search_console_verification_token}"]
# }