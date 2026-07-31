mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }
}

run "safe_foundation_plan" {
  command = plan

  variables {
    environment        = "test"
    monthly_budget_usd = 10
    enable_runtime     = false
    create_ci_role     = false
  }

  assert {
    condition     = length(aws_ecr_repository.service) == 3
    error_message = "The foundation must create three immutable service repositories."
  }

  assert {
    condition     = length(aws_bedrockagentcore_workload_identity.agent) == 3
    error_message = "Planner, Finance, and Email require distinct workload identities."
  }

  assert {
    condition     = length(aws_bedrockagentcore_agent_runtime.mcp) == 0
    error_message = "Runtime creation must remain disabled in the safe default plan."
  }

  assert {
    condition     = aws_budgets_budget.lab.limit_amount == "10"
    error_message = "A bounded monthly budget is mandatory."
  }
}

run "runtime_requires_immutable_inputs" {
  command = plan

  variables {
    environment    = "test"
    enable_runtime = true
  }

  expect_failures = [check.runtime_inputs]
}

run "runtime_plan_with_digest" {
  command = plan

  variables {
    environment        = "test"
    enable_runtime     = true
    mcp_image_uri      = "123456789012.dkr.ecr.us-east-1.amazonaws.com/phase12/secure-mcp@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    oidc_discovery_url = "https://identity.example.invalid/.well-known/openid-configuration"
  }

  assert {
    condition     = length(aws_bedrockagentcore_agent_runtime.mcp) == 1
    error_message = "A reviewed immutable image must create exactly one protected MCP runtime."
  }
}
