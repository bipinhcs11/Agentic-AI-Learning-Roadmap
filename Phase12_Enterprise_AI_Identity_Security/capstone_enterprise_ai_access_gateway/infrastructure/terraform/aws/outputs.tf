output "ecr_repository_urls" {
  description = "Container repositories keyed by Phase 12 service."
  value       = { for name, repository in aws_ecr_repository.service : name => repository.repository_url }
}

output "agent_workload_identity_arns" {
  description = "Distinct AgentCore identities for the fictional agent roles."
  value       = { for name, identity in aws_bedrockagentcore_workload_identity.agent : name => identity.workload_identity_arn }
}

output "mcp_runtime_arn" {
  description = "AgentCore MCP runtime ARN when runtime creation is enabled."
  value       = try(aws_bedrockagentcore_agent_runtime.mcp[0].agent_runtime_arn, null)
}

output "github_deployer_role_arn" {
  description = "Keyless GitHub Actions role ARN when CI identity creation is enabled."
  value       = try(aws_iam_role.github_deployer[0].arn, null)
}
