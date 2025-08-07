resource "google_cloud_run_v2_service" "service" {
  name = var.name
  project = var.project_id
  location = var.region
  deletion_protection = false
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = var.service_account_email
    max_instance_request_concurrency = 1

    containers {
      image = var.image
      #image = "gcr.io/google-samples/hello-app:1.0" # Sample image until real deployment

      resources {
        limits = {
          cpu = var.cpu
          memory = var.memory
        }
      }

      env {
        name = "MODEL_BUCKET"
        value = "${var.project_id}-${terraform.workspace}"
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
  }

  traffic {
    percent = 100
    type = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
}

resource "google_pubsub_topic" "topic" {
  name = "${var.name}-trigger"
  project = var.project_id
}

# Dead-letter topic to avoid retrying failed messages
resource "google_pubsub_topic" "dead_letter_topic" {
  name    = "${var.name}-dlq"
  project = var.project_id
}

# Grant Pub/Sub permission to publish to the dead letter topic
data "google_project" "project" {
  project_id = var.project_id
}

resource "google_pubsub_topic_iam_member" "allow_dlq_publish" {
  topic  = google_pubsub_topic.dead_letter_topic.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_cloud_scheduler_job" "scheduler" {
  name      = "${var.name}-scheduler"
  project   = var.project_id
  region    = var.region
  schedule  = var.schedule
  time_zone = "Europe/Copenhagen"

  pubsub_target {
    topic_name = google_pubsub_topic.topic.id
    data = base64encode("{}")
  }
}

resource "google_pubsub_subscription" "subscription" {
  name  = "${var.name}-subscription"
  topic = google_pubsub_topic.topic.id

  push_config {
    push_endpoint = google_cloud_run_v2_service.service.uri
    oidc_token {
      service_account_email = var.service_account_email
    }
  }

  ack_deadline_seconds = 600

  # Only deliver the message once, then send to DLQ
  dead_letter_policy {
    dead_letter_topic = google_pubsub_topic.dead_letter_topic.id
    max_delivery_attempts = 5
  }
}
