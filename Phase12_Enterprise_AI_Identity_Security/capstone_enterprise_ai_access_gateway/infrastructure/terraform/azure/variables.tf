variable "subscription_id" {
  description = "Dedicated Azure sandbox subscription ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "subscription_id must be a GUID from a dedicated sandbox subscription."
  }
}

variable "location" {
  description = "Azure region for the isolated learning environment."
  type        = string
  default     = "centralus"
}

variable "environment" {
  description = "Short environment name used in resources and tags."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,10}$", var.environment))
    error_message = "environment must be 2-11 lowercase letters, digits, or hyphens."
  }
}

variable "name_suffix" {
  description = "Globally unique lowercase suffix used by the container registry."
  type        = string
  default     = "lab001"

  validation {
    condition     = can(regex("^[a-z0-9]{5,12}$", var.name_suffix))
    error_message = "name_suffix must contain 5-12 lowercase letters or digits."
  }
}

variable "owner" {
  description = "Fictional or team owner label. Do not place personal data here."
  type        = string
  default     = "phase12-learning"
}

variable "monthly_budget_usd" {
  description = "Mandatory monthly sandbox budget. Azure bills in the billing currency."
  type        = number
  default     = 25

  validation {
    condition     = var.monthly_budget_usd > 0 && var.monthly_budget_usd <= 100
    error_message = "The learning budget must be greater than 0 and no more than 100."
  }
}

variable "budget_start_date" {
  description = "First day of the current month in RFC3339 form, such as 2026-07-01T00:00:00Z."
  type        = string
}

variable "budget_contact_emails" {
  description = "Verified contacts that receive the mandatory Azure budget notification."
  type        = set(string)
  sensitive   = true

  validation {
    condition     = length(var.budget_contact_emails) > 0
    error_message = "At least one budget contact is required before Azure resources are planned."
  }
}

variable "enable_runtime" {
  description = "Creates Container Apps only after immutable image digests are supplied."
  type        = bool
  default     = false
}

variable "service_images" {
  description = "Immutable ACR image URIs keyed by identity, gateway, mcp, and opa."
  type        = map(string)
  default     = {}
}

variable "github_repository" {
  description = "GitHub owner/repository trusted by the Azure federated credential."
  type        = string
  default     = "bipinhcs11/Agentic-AI-Learning-Roadmap"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use owner/repository format."
  }
}

variable "github_branch" {
  description = "Only this branch may exchange a GitHub OIDC token for the deployer identity."
  type        = string
  default     = "main"
}
