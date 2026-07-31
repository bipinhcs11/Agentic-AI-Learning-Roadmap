locals {
  name_prefix = "phase12-${var.environment}"
  agents      = toset(["planner", "finance", "email"])
  repositories = toset([
    "identity-service",
    "delegation-gateway",
    "secure-mcp"
  ])

  common_tags = {
    Project     = "phase12-enterprise-ai-identity"
    Environment = var.environment
    Owner       = var.owner
    DataClass   = "fictional-educational"
    ManagedBy   = "terraform"
    AutoDestroy = "required"
  }
}

check "runtime_inputs" {
  assert {
    condition = !var.enable_runtime || (
      can(regex("^[0-9]+\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/.+@sha256:[0-9a-f]{64}$", var.mcp_image_uri)) &&
      endswith(var.oidc_discovery_url, ".well-known/openid-configuration")
    )
    error_message = "Runtime deployment requires an immutable ECR digest and an OIDC discovery URL."
  }
}

check "ci_identity_inputs" {
  assert {
    condition = !var.create_ci_role || can(regex(
      "^arn:aws:iam::[0-9]{12}:oidc-provider/token\\.actions\\.githubusercontent\\.com$",
      var.github_oidc_provider_arn
    ))
    error_message = "create_ci_role requires the account's existing GitHub OIDC provider ARN."
  }
}

resource "aws_budgets_budget" "lab" {
  name         = "${local.name_prefix}-monthly-limit"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = length(var.budget_alert_emails) == 0 ? [] : [1]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = 80
      threshold_type             = "PERCENTAGE"
      notification_type          = "FORECASTED"
      subscriber_email_addresses = var.budget_alert_emails
    }
  }
}

resource "aws_ecr_repository" "service" {
  for_each = local.repositories

  name                 = "${local.name_prefix}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "service" {
  for_each = aws_ecr_repository.service

  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Retain only ten learning images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "service" {
  for_each = local.repositories

  name              = "/phase12/${var.environment}/${each.key}"
  retention_in_days = 14
}

resource "aws_bedrockagentcore_workload_identity" "agent" {
  for_each = local.agents

  name = "${local.name_prefix}-${each.key}-agent"
}

data "aws_iam_policy_document" "agentcore_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "agentcore_runtime" {
  name               = "${local.name_prefix}-agentcore-runtime"
  assume_role_policy = data.aws_iam_policy_document.agentcore_assume.json
}

data "aws_iam_policy_document" "agentcore_runtime" {
  statement {
    sid       = "GetECRAuthorizationToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "ReadOnlyMCPImage"
    effect = "Allow"
    actions = [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
    ]
    resources = [aws_ecr_repository.service["secure-mcp"].arn]
  }

  statement {
    sid    = "WriteRuntimeLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.service["secure-mcp"].arn}:*"]
  }
}

resource "aws_iam_role_policy" "agentcore_runtime" {
  name   = "${local.name_prefix}-runtime-minimum"
  role   = aws_iam_role.agentcore_runtime.id
  policy = data.aws_iam_policy_document.agentcore_runtime.json
}

resource "aws_bedrockagentcore_agent_runtime" "mcp" {
  count = var.enable_runtime ? 1 : 0

  agent_runtime_name = replace("${local.name_prefix}_secure_mcp", "-", "_")
  description        = "Fictional Phase 12 MCP security lab"
  role_arn           = aws_iam_role.agentcore_runtime.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = var.mcp_image_uri
    }
  }

  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url    = var.oidc_discovery_url
      allowed_audience = [var.oidc_audience]
      allowed_scopes   = ["invoice.read", "email.draft"]
    }
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  protocol_configuration {
    server_protocol = "MCP"
  }

  lifecycle_configuration {
    idle_runtime_session_timeout = 900
    max_lifetime                 = 3600
  }

  depends_on = [aws_iam_role_policy.agentcore_runtime]
}

data "aws_iam_policy_document" "github_deployer_assume" {
  count = var.create_ci_role ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:ref:refs/heads/${var.github_branch}"]
    }
  }
}

resource "aws_iam_role" "github_deployer" {
  count = var.create_ci_role ? 1 : 0

  name                 = "${local.name_prefix}-github-deployer"
  assume_role_policy   = data.aws_iam_policy_document.github_deployer_assume[0].json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "github_deployer" {
  count = var.create_ci_role ? 1 : 0

  statement {
    sid       = "GetECRAuthorizationToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "PublishImagesToPhase12Repositories"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ]
    resources = [for repository in aws_ecr_repository.service : repository.arn]
  }
}

resource "aws_iam_role_policy" "github_deployer" {
  count = var.create_ci_role ? 1 : 0

  name   = "${local.name_prefix}-publish-images"
  role   = aws_iam_role.github_deployer[0].id
  policy = data.aws_iam_policy_document.github_deployer[0].json
}
