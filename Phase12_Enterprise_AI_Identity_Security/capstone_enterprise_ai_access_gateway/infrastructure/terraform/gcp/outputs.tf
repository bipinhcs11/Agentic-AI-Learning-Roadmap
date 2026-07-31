output "artifact_registry_repository" {
  description = "Artifact Registry repository containing immutable Phase 12 images."
  value       = google_artifact_registry_repository.phase12.name
}

output "service_account_emails" {
  description = "Runtime service accounts keyed by service."
  value       = { for name, account in google_service_account.service : name => account.email }
}

output "agent_service_account_emails" {
  description = "Distinct fictional agent identities."
  value       = { for name, account in google_service_account.agent : name => account.email }
}

output "workload_identity_provider" {
  description = "Provider name used by GitHub Actions keyless authentication."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_deployer_service_account" {
  description = "Service account impersonated by the restricted GitHub identity."
  value       = google_service_account.github_deployer.email
}

output "gateway_url" {
  description = "Public gateway URI when runtime deployment is enabled."
  value       = try(google_cloud_run_v2_service.service["gateway"].uri, null)
}
