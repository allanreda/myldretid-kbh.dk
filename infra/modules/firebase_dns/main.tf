# Create DNS managed zone to host DNS records for custom domain
resource "google_dns_managed_zone" "myldretid-kbh-zone" {
  name = "myldretid-kbh-zone"
  dns_name = "${var.custom_domain_name}."
  project = var.project_id
  # Domain Name System Security Extensions
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

# Create A record that maps domain to IPv4 address
resource "google_dns_record_set" "firebase_a_record" {
  name         = "${var.custom_domain_name}."
  type         = "A"
  ttl          = 300
  project = var.project_id
  managed_zone = google_dns_managed_zone.myldretid-kbh-zone.name

  rrdatas = [var.dns_ip]
}

# TXT record for domain verification
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

# CNAME record for www subdomain pointing to Firebase Hosting target
resource "google_dns_record_set" "firebase_www_cname" {
  name         = "www.${var.custom_domain_name}."
  type         = "CNAME"
  ttl          = 300
  project      = var.project_id
  managed_zone = google_dns_managed_zone.myldretid-kbh-zone.name

  rrdatas = ["myldretid-kbh.web.app."]
}
