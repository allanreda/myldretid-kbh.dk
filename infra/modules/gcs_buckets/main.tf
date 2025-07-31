# Ressource to create bucket in GCS
resource "google_storage_bucket" "bucket" {
  name     = var.name
  project = var.project_id
  location = var.region
  uniform_bucket_level_access = true
  force_destroy = true

# Optional CORS block
  dynamic "cors" {
    # Only add CORS if enable_cors = true and domain is not null
    for_each = var.enable_cors && var.domain != null ? [1] : []

    origin          = [var.domain] # Get website domain
    method          = ["GET"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }

}


# Optional public read access
resource "google_storage_bucket_iam_member" "public_read" {
  count  = var.make_public ? 1 : 0
  bucket = google_storage_bucket.bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}