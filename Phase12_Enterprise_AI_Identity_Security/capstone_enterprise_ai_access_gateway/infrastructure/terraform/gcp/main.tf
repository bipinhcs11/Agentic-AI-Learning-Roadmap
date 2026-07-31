locals {
  name_prefix = "phase12-${var.environment}"
  services = {
    identity = { port = 8081, public = false }
    gateway  = { port = 8084, public = true }
    mcp      = { port = 8086, public = false }
    opa      = { port = 8181, public = false }
  }
  agents = toset(["planner", "finance", "email"])

  runtime_images_valid = (
    length(setsubtract(toset(keys(local.services)), toset(keys(var.service_images)))) == 0 &&
    alltrue([for image in values(var.service_images) : can(regex("@sha256:[0-9a-f]{64}$", image))])
  )
  runtime_services = var.enable_runtime && local.runtime_images_valid ? local.services : {}

  required_apis = toset([
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sts.googleapis.com"
  ])

  common_labels = {
    project      = "phase12-ai-identity"
    environment  = var.environment
    owner        = var.owner
    data_class   = "fictional-educational"
    managed_by   = "terraform"
    auto_destroy = "required"
  }
}

check "runtime_images" {
  assert {
    condition     = !var.enable_runtime || local.runtime_images_valid
    error_message = "Runtime deployment requires immutable digest images for identity, gateway, mcp, and opa."
  }
}

data "google_project" "phase12" {
  project_id = var.project_id
}

resource "google_project_service" "required" {
  for_each = local.required_apis

  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_billing_budget" "lab" {
  billing_account = var.billing_account_id
  display_name    = "${local.name_prefix}-monthly-limit"

  budget_filter {
    projects        = ["projects/${data.google_project.phase12.number}"]
    calendar_period = "MONTH"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "FORECASTED_SPEND"
  }

  deletion_policy = "DELETE"

  depends_on = [google_project_service.required["billingbudgets.googleapis.com"]]
}

resource "google_artifact_registry_repository" "phase12" {
  location      = var.region
  repository_id = "${local.name_prefix}-services"
  description   = "Fictional Phase 12 service images"
  format        = "DOCKER"
  labels        = local.common_labels

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-ten-newest"
    action = "KEEP"

    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-old-images"
    action = "DELETE"

    condition {
      older_than = "1209600s"
    }
  }

  depends_on = [google_project_service.required["artifactregistry.googleapis.com"]]
}

resource "google_service_account" "service" {
  for_each = local.services

  account_id   = "${local.name_prefix}-${each.key}"
  display_name = "Phase 12 ${title(each.key)} service"
  description  = "Fictional educational workload identity"
}

resource "google_service_account" "agent" {
  for_each = local.agents

  account_id   = "${local.name_prefix}-${each.key}-agent"
  display_name = "Phase 12 ${title(each.key)} agent"
  description  = "Fictional educational agent identity"
}

resource "google_service_account" "github_deployer" {
  account_id   = "${local.name_prefix}-github"
  display_name = "Phase 12 GitHub deployer"
  description  = "Keyless CI/CD identity restricted to one repository and branch"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "${local.name_prefix}-github"
  display_name              = "Phase 12 GitHub"
  description               = "GitHub Actions identities for the Phase 12 learning deployment"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions"
  display_name                       = "GitHub Actions"
  description                        = "Restricted repository and branch federation"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  attribute_condition = join(" && ", [
    "assertion.repository_owner_id == '${var.github_repository_owner_id}'",
    "attribute.repository == '${var.github_repository}'",
    "attribute.ref == 'refs/heads/${var.github_branch}'"
  ])

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_workload_user" {
  service_account_id = google_service_account.github_deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_artifact_registry_repository_iam_member" "github_writer" {
  location   = google_artifact_registry_repository.phase12.location
  repository = google_artifact_registry_repository.phase12.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.github_deployer.email}"
}

resource "google_secret_manager_secret" "runtime_configuration" {
  for_each = toset(["identity-broker-token", "jwt-signing-material"])

  secret_id = "${local.name_prefix}-${each.key}"
  labels    = local.common_labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.required["secretmanager.googleapis.com"]]
}

resource "google_cloud_run_v2_service" "service" {
  for_each = local.runtime_services

  name                = "${local.name_prefix}-${each.key}"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false
  labels              = local.common_labels

  template {
    service_account = google_service_account.service[each.key].email

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = var.service_images[each.key]

      ports {
        container_port = each.value.port
      }

      env {
        name  = "PHASE12_DATA_CLASS"
        value = "fictional-educational"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }
    }
  }

  depends_on = [google_project_service.required["run.googleapis.com"]]
}

resource "google_cloud_run_v2_service_iam_member" "gateway_public" {
  count = contains(keys(local.runtime_services), "gateway") ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.service["gateway"].location
  name     = google_cloud_run_v2_service.service["gateway"].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "gateway_to_internal" {
  for_each = {
    for name, service in local.runtime_services : name => service if !service.public
  }

  project  = var.project_id
  location = google_cloud_run_v2_service.service[each.key].location
  name     = google_cloud_run_v2_service.service[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.service["gateway"].email}"
}
