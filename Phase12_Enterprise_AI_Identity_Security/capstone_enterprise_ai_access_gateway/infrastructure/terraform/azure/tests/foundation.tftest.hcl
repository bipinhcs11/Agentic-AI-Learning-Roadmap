mock_provider "azurerm" {}

run "safe_foundation_plan" {
  command = plan

  variables {
    subscription_id       = "00000000-0000-0000-0000-000000000000"
    environment           = "test"
    name_suffix           = "test001"
    monthly_budget_usd    = 10
    budget_start_date     = "2026-07-01T00:00:00Z"
    budget_contact_emails = ["test@example.com"]
    enable_runtime        = false
  }

  assert {
    condition     = length(azurerm_user_assigned_identity.service) == 4
    error_message = "Every runtime service requires a separate managed identity."
  }

  assert {
    condition     = length(azurerm_user_assigned_identity.agent) == 3
    error_message = "Planner, Finance, and Email require distinct identities."
  }

  assert {
    condition     = length(azurerm_container_app.service) == 0
    error_message = "Container Apps must remain disabled in the safe default plan."
  }

  assert {
    condition     = azurerm_container_registry.phase12.admin_enabled == false
    error_message = "The ACR administrator account must remain disabled."
  }
}

run "runtime_requires_immutable_images" {
  command = plan

  variables {
    subscription_id       = "00000000-0000-0000-0000-000000000000"
    environment           = "test"
    name_suffix           = "test001"
    budget_start_date     = "2026-07-01T00:00:00Z"
    budget_contact_emails = ["test@example.com"]
    enable_runtime        = true
  }

  expect_failures = [check.runtime_images]
}

run "runtime_plan_with_digests" {
  command = plan

  variables {
    subscription_id       = "00000000-0000-0000-0000-000000000000"
    environment           = "test"
    name_suffix           = "test001"
    budget_start_date     = "2026-07-01T00:00:00Z"
    budget_contact_emails = ["test@example.com"]
    enable_runtime        = true
    service_images = {
      identity = "phase12test001.azurecr.io/identity@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      gateway  = "phase12test001.azurecr.io/gateway@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      mcp      = "phase12test001.azurecr.io/mcp@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      opa      = "phase12test001.azurecr.io/opa@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }
  }

  assert {
    condition     = length(azurerm_container_app.service) == 4
    error_message = "A reviewed image set must create the four isolated Container Apps."
  }

  assert {
    condition     = azurerm_container_app.service["gateway"].ingress[0].external_enabled
    error_message = "Only the gateway is intended to expose external ingress."
  }

  assert {
    condition = alltrue([
      for name in ["identity", "mcp", "opa"] :
      !azurerm_container_app.service[name].ingress[0].external_enabled
    ])
    error_message = "Identity, MCP, and OPA must use internal ingress."
  }
}
