# # Define data source for service account
# data "google_service_account" "hyggeskyen_sa" {
#     account_id = var.service_account_email
#     project = var.external_project_id
# }

# # Assign project-level IAM roles to service account
# resource "google_project_iam_member" "project_roles" {
#     # Loop to assign the roles passed down from permissions/vars.tf
#     for_each = { for r in var.project_level_roles : r.role => r }

#     project = var.project_id # Project ID passed down from permissions/vars.tf
#     role    = each.value.role # Defined roles
#     member =  data.google_service_account.hyggeskyen_sa.member 
# } 



resource "google_service_account" "deployment_sa" {
  account_id   = var.service_account_name      
  project      = var.project_id                   
}

resource "google_project_iam_member" "project_roles" {
  for_each = { for r in var.project_level_roles : r.role => r }

  project = var.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.deployment_sa.email}"
}

