variable "project_id" {
  description = "Dedicated Google Cloud sandbox project ID."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid dedicated Google Cloud project ID."
  }
}

variable "billing_account_id" {
  description = "Billing account used only to create the mandatory project-scoped budget."
  type        = string

  validation {
    condition     = can(regex("^[0-9A-F]{6}-[0-9A-F]{6}-[0-9A-F]{6}$", var.billing_account_id))
    error_message = "billing_account_id must use 000000-000000-000000 format."
  }
}

variable "region" {
  description = "Google Cloud region for the isolated learning environment."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Short environment name used in resources and labels."
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
  description = "Mandatory monthly project budget in USD."
  type        = number
  default     = 25

  validation {
    condition     = var.monthly_budget_usd > 0 && var.monthly_budget_usd <= 100
    error_message = "The learning budget must be greater than 0 and no more than 100 USD."
  }
}

variable "enable_runtime" {
  description = "Creates Cloud Run services only after immutable image digests are supplied."
  type        = bool
  default     = false
}

variable "service_images" {
  description = "Immutable Artifact Registry image URIs keyed by identity, gateway, mcp, and opa."
  type        = map(string)
  default     = {}
}

variable "github_repository" {
  description = "GitHub owner/repository trusted by Workload Identity Federation."
  type        = string
  default     = "bipinhcs11/Agentic-AI-Learning-Roadmap"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use owner/repository format."
  }
}

variable "github_repository_owner_id" {
  description = "Immutable numeric GitHub owner ID used to prevent repository-name takeover."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_owner_id))
    error_message = "github_repository_owner_id must be the immutable numeric GitHub owner ID."
  }
}

variable "github_branch" {
  description = "Only this branch may exchange GitHub OIDC tokens for Google credentials."
  type        = string
  default     = "main"
}
