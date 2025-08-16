
# Enable all required APIs in the project
module "enable_apis" {
  source = "./modules/api_activation"
  project_id = var.project_id
  api_list = var.api_list
}

# Call the Permissions module to grant SA required permissions
module "permissions" {
  source = "./modules/permissions"
  
  project_id = var.project_id # Passes project_id down to permissions module
  external_project_id = var.external_project_id
  service_account_name = var.service_account_name
  project_level_roles = var.project_level_roles # Passes the list of the required project level roles for the hyggeskyen SA down
  cicd_service_account_email = var.cicd_service_account_email
  cicd_project_level_roles = var.cicd_project_level_roles
  # Wait for APIs to be enabled
  depends_on = [module.enable_apis]
}

# Create bucket to store trained models
module "models_bucket" {
  source = "./modules/gcs_buckets"
  name = "${var.project_id}-${terraform.workspace}-models"
  project_id = var.project_id
  region = var.region
  enable_cors = false
  make_public = false
 
  # Wait for APIs to be enabled
  depends_on = [module.permissions]
}

# Create bucket to store prediction file
module "predictions_bucket" {
  source = "./modules/gcs_buckets"
  name = "${var.project_id}-${terraform.workspace}-predictions"
  project_id = var.project_id
  region = var.region
  domain = var.domain
  enable_cors = true
  make_public = true

  # Wait for APIs to be enabled
  depends_on = [module.permissions]
}

resource "google_artifact_registry_repository" "pipeline_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "myldretid-kbh-${terraform.workspace}"  
  format        = "DOCKER"

  # Wait for APIs to be enabled
  depends_on = [module.permissions]
}

module "training_pipeline" {
  source = "./modules/cloud_run_pipeline"
  name = "training-${terraform.workspace}"
  project_id = var.project_id
  region = var.region
  service_account_email = var.service_account_email
  image = "${var.region}-docker.pkg.dev/${var.project_id}/myldretid-kbh-${terraform.workspace}/training:latest"
  cpu = 2
  memory = "1024Mi"
  schedule = "0 6 * * 0" # Every sunday at 6:00 

  # Wait for repo to be created
  depends_on = [google_artifact_registry_repository.pipeline_repo]
}

module "prediction_pipeline_morning" {
  source = "./modules/cloud_run_pipeline"
  name = "prediction-morning-${terraform.workspace}"
  project_id = var.project_id
  region = var.region
  service_account_email = var.service_account_email
  image = "${var.region}-docker.pkg.dev/${var.project_id}/myldretid-kbh-${terraform.workspace}/prediction:latest"
  cpu = 1
  memory = "512Mi"
  schedule = "0 18 * * *"  # Every day at 18:00 

  # Wait for repo to be created
  depends_on = [google_artifact_registry_repository.pipeline_repo]
}

module "prediction_pipeline_afternoon" {
  source = "./modules/cloud_run_pipeline"
  name = "prediction-afternoon-${terraform.workspace}"
  project_id = var.project_id
  region = var.region
  service_account_email = var.service_account_email
  image = "${var.region}-docker.pkg.dev/${var.project_id}/myldretid-kbh-${terraform.workspace}/prediction:latest"
  cpu = 1
  memory = "512Mi"
  schedule = "0 10 * * *"  # Every day at 11:00 

  # Wait for repo to be created
  depends_on = [google_artifact_registry_repository.pipeline_repo]
}