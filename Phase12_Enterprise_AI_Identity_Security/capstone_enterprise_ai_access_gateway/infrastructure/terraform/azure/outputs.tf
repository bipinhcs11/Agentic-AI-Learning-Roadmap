output "resource_group_name" {
  description = "Dedicated Phase 12 resource group."
  value       = azurerm_resource_group.phase12.name
}

output "container_registry_login_server" {
  description = "ACR host used by immutable Phase 12 images."
  value       = azurerm_container_registry.phase12.login_server
}

output "service_identity_client_ids" {
  description = "Managed identity client IDs keyed by service."
  value       = { for name, identity in azurerm_user_assigned_identity.service : name => identity.client_id }
}

output "agent_identity_principal_ids" {
  description = "Distinct managed identity principals for fictional agents."
  value       = { for name, identity in azurerm_user_assigned_identity.agent : name => identity.principal_id }
}

output "gateway_url" {
  description = "Public gateway URL when runtime deployment is enabled."
  value       = try("https://${azurerm_container_app.service["gateway"].latest_revision_fqdn}", null)
}

output "github_deployer_client_id" {
  description = "Client ID used by GitHub OIDC login; this is not a secret."
  value       = azurerm_user_assigned_identity.github_deployer.client_id
}
