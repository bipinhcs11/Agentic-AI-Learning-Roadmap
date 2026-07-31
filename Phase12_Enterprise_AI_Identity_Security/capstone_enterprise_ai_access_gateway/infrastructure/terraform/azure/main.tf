locals {
  name_prefix = "phase12-${var.environment}"
  services = {
    identity = { port = 8081, external = false }
    gateway  = { port = 8084, external = true }
    mcp      = { port = 8086, external = false }
    opa      = { port = 8181, external = false }
  }
  agents = toset(["planner", "finance", "email"])

  runtime_images_valid = (
    length(setsubtract(toset(keys(local.services)), toset(keys(var.service_images)))) == 0 &&
    alltrue([for image in values(var.service_images) : can(regex("@sha256:[0-9a-f]{64}$", image))])
  )
  runtime_services = var.enable_runtime && local.runtime_images_valid ? local.services : {}

  common_tags = {
    Project     = "phase12-enterprise-ai-identity"
    Environment = var.environment
    Owner       = var.owner
    DataClass   = "fictional-educational"
    ManagedBy   = "terraform"
    AutoDestroy = "required"
  }
}

check "runtime_images" {
  assert {
    condition     = !var.enable_runtime || local.runtime_images_valid
    error_message = "Runtime deployment requires immutable digest images for identity, gateway, mcp, and opa."
  }
}

check "budget_start" {
  assert {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-01T00:00:00Z$", var.budget_start_date))
    error_message = "budget_start_date must be the first day of a month at 00:00:00Z."
  }
}

resource "azurerm_resource_group" "phase12" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_consumption_budget_resource_group" "lab" {
  name              = "${local.name_prefix}-monthly-limit"
  resource_group_id = azurerm_resource_group.phase12.id
  amount            = var.monthly_budget_usd
  time_grain        = "Monthly"

  time_period {
    start_date = var.budget_start_date
  }

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Forecasted"
    contact_emails = var.budget_contact_emails
  }
}

resource "azurerm_log_analytics_workspace" "phase12" {
  name                = "log-${local.name_prefix}"
  location            = azurerm_resource_group.phase12.location
  resource_group_name = azurerm_resource_group.phase12.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

resource "azurerm_container_registry" "phase12" {
  name                          = "phase12${var.environment}${var.name_suffix}"
  resource_group_name           = azurerm_resource_group.phase12.name
  location                      = azurerm_resource_group.phase12.location
  sku                           = "Basic"
  admin_enabled                 = false
  anonymous_pull_enabled        = false
  public_network_access_enabled = true
  tags                          = local.common_tags
}

resource "azurerm_container_app_environment" "phase12" {
  name                       = "cae-${local.name_prefix}"
  location                   = azurerm_resource_group.phase12.location
  resource_group_name        = azurerm_resource_group.phase12.name
  logs_destination           = "log-analytics"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.phase12.id
  mutual_tls_enabled         = true
  tags                       = local.common_tags
}

resource "azurerm_user_assigned_identity" "service" {
  for_each = local.services

  name                = "id-${local.name_prefix}-${each.key}"
  location            = azurerm_resource_group.phase12.location
  resource_group_name = azurerm_resource_group.phase12.name
  tags                = local.common_tags
}

resource "azurerm_user_assigned_identity" "agent" {
  for_each = local.agents

  name                = "id-${local.name_prefix}-${each.key}-agent"
  location            = azurerm_resource_group.phase12.location
  resource_group_name = azurerm_resource_group.phase12.name
  tags                = local.common_tags
}

resource "azurerm_role_assignment" "service_acr_pull" {
  for_each = azurerm_user_assigned_identity.service

  scope                            = azurerm_container_registry.phase12.id
  role_definition_name             = "AcrPull"
  principal_id                     = each.value.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_user_assigned_identity" "github_deployer" {
  name                = "id-${local.name_prefix}-github-deployer"
  location            = azurerm_resource_group.phase12.location
  resource_group_name = azurerm_resource_group.phase12.name
  tags                = local.common_tags
}

resource "azurerm_federated_identity_credential" "github_deployer" {
  name                      = "github-${var.environment}-${var.github_branch}"
  user_assigned_identity_id = azurerm_user_assigned_identity.github_deployer.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = "repo:${var.github_repository}:ref:refs/heads/${var.github_branch}"
}

resource "azurerm_role_assignment" "github_acr_push" {
  scope                            = azurerm_container_registry.phase12.id
  role_definition_name             = "AcrPush"
  principal_id                     = azurerm_user_assigned_identity.github_deployer.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_container_app" "service" {
  for_each = local.runtime_services

  name                         = "ca-${local.name_prefix}-${each.key}"
  container_app_environment_id = azurerm_container_app_environment.phase12.id
  resource_group_name          = azurerm_resource_group.phase12.name
  revision_mode                = "Single"
  max_inactive_revisions       = 2
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.service[each.key].id]
  }

  registry {
    server   = azurerm_container_registry.phase12.login_server
    identity = azurerm_user_assigned_identity.service[each.key].id
  }

  ingress {
    external_enabled = each.value.external
    target_port      = each.value.port
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 0
    max_replicas = 2

    container {
      name   = each.key
      image  = var.service_images[each.key]
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "PHASE12_DATA_CLASS"
        value = "fictional-educational"
      }
    }
  }

  depends_on = [azurerm_role_assignment.service_acr_pull]
}
