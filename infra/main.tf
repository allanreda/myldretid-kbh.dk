
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
  service_account_email = var.service_account_email
  project_level_roles = var.project_level_roles # Passes the list of the required project level roles for the hyggeskyen SA down

  # Wait for APIs to be enabled
  depends_on = [module.enable_apis]
}

# Create bucket to store trained models
module "models_bucket" {
  source = "./modules/gcs_buckets"
  name = "${terraform.workspace}-models"
  project_id = var.project_id
  region = var.region
  enable_cors = false
  make_public = false

  # Wait for APIs to be enabled
  depends_on = [module.enable_apis]
}

# Create bucket to store prediction file
module "predictions_bucket" {
  source = "./modules/gcs_buckets"
  name = "${terraform.workspace}-predictions"
  project_id = var.project_id
  region = var.region
  domain = var.domain
  enable_cors = true
  make_public = true

  # Wait for APIs to be enabled
  depends_on = [module.enable_apis]
}
