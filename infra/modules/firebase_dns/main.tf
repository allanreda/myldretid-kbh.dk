
resource "google_dns_managed_zone" "myldretid-kbh-zone" {
  name = "myldretid-kbh-zone"
  dns_name = "${var.custom_domain_name}."
  project = var.project_id
}

resource "google_dns_record_set" "firebase_a_record" {
  name         = "${var.custom_domain_name}."
  type         = "A"
  ttl          = 300
  project = var.project_id
  managed_zone = google_dns_managed_zone.myldretid-kbh-zone.name

  rrdatas = [var.dns_ip]

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_dns_record_set" "firebase_txt_verification" {
  name         = "__firebase.__acme-challenge.${var.custom_domain_name}."
  type         = "TXT"
  ttl          = 300
  project = var.project_id
  managed_zone = google_dns_managed_zone.myldretid-kbh-zone.name

  rrdatas = ["\"${var.txt_value}\""]

  lifecycle {
    prevent_destroy = true
  }
}