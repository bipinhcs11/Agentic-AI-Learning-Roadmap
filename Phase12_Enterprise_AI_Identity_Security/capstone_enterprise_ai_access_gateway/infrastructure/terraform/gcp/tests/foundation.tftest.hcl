mock_provider "google" {
  mock_data "google_project" {
    defaults = {
      number = "123456789012"
    }
  }
}

run "safe_foundation_plan" {
  command = plan

  variables {
    project_id                 = "phase12-test-project"
    billing_account_id         = "000000-000000-000000"
    environment                = "test"
    monthly_budget_usd         = 10
    github_repository_owner_id = "12345678"
    enable_runtime             = false
  }

  assert {
    condition     = length(google_service_account.service) == 4
    error_message = "Every runtime service requires a separate service account."
  }

  assert {
    condition     = length(google_service_account.agent) == 3
    error_message = "Planner, Finance, and Email require distinct service accounts."
  }

  assert {
    condition     = length(google_cloud_run_v2_service.service) == 0
    error_message = "Cloud Run must remain disabled in the safe default plan."
  }

  assert {
    condition     = google_billing_budget.lab.amount[0].specified_amount[0].units == "10"
    error_message = "A bounded project budget is mandatory."
  }
}

run "runtime_requires_immutable_images" {
  command = plan

  variables {
    project_id                 = "phase12-test-project"
    billing_account_id         = "000000-000000-000000"
    environment                = "test"
    github_repository_owner_id = "12345678"
    enable_runtime             = true
  }

  expect_failures = [check.runtime_images]
}

run "runtime_plan_with_digests" {
  command = plan

  variables {
    project_id                 = "phase12-test-project"
    billing_account_id         = "000000-000000-000000"
    environment                = "test"
    github_repository_owner_id = "12345678"
    enable_runtime             = true
    service_images = {
      identity = "us-central1-docker.pkg.dev/phase12-test-project/phase12/identity@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      gateway  = "us-central1-docker.pkg.dev/phase12-test-project/phase12/gateway@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      mcp      = "us-central1-docker.pkg.dev/phase12-test-project/phase12/mcp@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      opa      = "us-central1-docker.pkg.dev/phase12-test-project/phase12/opa@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }
  }

  assert {
    condition     = length(google_cloud_run_v2_service.service) == 4
    error_message = "A reviewed image set must create the four isolated Cloud Run services."
  }

  assert {
    condition     = length(google_cloud_run_v2_service_iam_member.gateway_public) == 1
    error_message = "Only the gateway receives the explicit public invoker binding."
  }

  assert {
    condition     = length(google_cloud_run_v2_service_iam_member.gateway_to_internal) == 3
    error_message = "Identity, MCP, and OPA must accept only the gateway runtime identity."
  }
}
