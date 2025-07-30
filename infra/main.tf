
module "enable_apis" {
  source = "./modules/api_activation"
  project_id = var.project_id
  api_list = var.api_list
}
# Call the Permissions module
module "permissions" {
  source = "./modules/permissions"
  
  project_id = var.project_id # Passes project_id down to permissions module
  project_level_roles = var.project_level_roles # Passes the list of the required project level roles for the hyggeskyen SA down
}
