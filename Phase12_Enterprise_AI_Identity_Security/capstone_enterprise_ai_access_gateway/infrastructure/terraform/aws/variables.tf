variable "aws_region" {
  description = "AWS region used by the isolated learning environment."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Short environment name used in resource names and tags."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,10}$", var.environment))
    error_message = "environment must be 2-11 lowercase letters, digits, or hyphens."
  }
}

variable "owner" {
  description = "Fictional or team owner label. Do not place personal data here."
  type        = string
  default     = "phase12-learning"
}

variable "monthly_budget_usd" {
  description = "Mandatory monthly lab budget in USD."
  type        = number
  default     = 25

  validation {
    condition     = var.monthly_budget_usd > 0 && var.monthly_budget_usd <= 100
    error_message = "The learning budget must be greater than 0 and no more than 100 USD."
  }
}

variable "budget_alert_emails" {
  description = "Optional verified email addresses for AWS Budget alerts."
  type        = set(string)
  default     = []
  sensitive   = true
}

variable "enable_runtime" {
  description = "Creates the AgentCore MCP runtime only after images and issuer values are configured."
  type        = bool
  default     = false
}

variable "mcp_image_uri" {
  description = "Immutable ECR image URI for the secure MCP server, including an @sha256 digest."
  type        = string
  default     = ""
}

variable "oidc_discovery_url" {
  description = "Public OIDC discovery URL used by the AgentCore JWT authorizer."
  type        = string
  default     = ""
}

variable "oidc_audience" {
  description = "Audience accepted by the AgentCore JWT authorizer."
  type        = string
  default     = "phase12-secure-mcp"
}

variable "create_ci_role" {
  description = "Creates a GitHub Actions deployment role using an existing GitHub OIDC provider."
  type        = bool
  default     = false
}

variable "github_oidc_provider_arn" {
  description = "ARN of the account's existing token.actions.githubusercontent.com OIDC provider."
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub owner/repository allowed to request the deployment role."
  type        = string
  default     = "bipinhcs11/Agentic-AI-Learning-Roadmap"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use owner/repository format."
  }
}

variable "github_branch" {
  description = "Only this branch may request the deployment role."
  type        = string
  default     = "main"
}
