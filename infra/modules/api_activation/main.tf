resource "google_project_service" "enabled_apis" {
    # Loop to assign the APIs passed down from api_activation/vars.tf
    for_each = toset(var.api_list)

    service = each.key # Defined API
    project = var.project_id # Project ID passed down from permissions/vars.tf

    disable_on_destroy = true 
    disable_dependent_services=true
}
