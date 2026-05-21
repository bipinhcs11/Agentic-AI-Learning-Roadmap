# ============================================================
# infrastructure/variables.tf
#
# WHAT: Declares all input variables for the Terraform
#       configuration. Variables make Terraform reusable —
#       the same code deploys to dev, staging, or prod by
#       changing variable values, not the code itself.
#
# WHY:  Hard-coding account IDs, regions, and image URIs into
#       main.tf would make it non-portable and a security risk
#       (accidentally committing account IDs to git). Variables
#       let you supply these at apply time or via .tfvars files.
#
# USAGE:
#   terraform apply -var="aws_account_id=123456789012" \
#                   -var="api_image_uri=123.dkr.ecr..."
#   # Or create a terraform.tfvars file (see deploy.sh)
# ============================================================

# ── AWS Provider variables ────────────────────────────────────

variable "aws_region" {
  description = "AWS region where all resources will be created. ECS Fargate is available in all major regions. us-east-1 (N. Virginia) is typically cheapest."
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "Your 12-digit AWS account ID. Used to construct ECR image URIs and IAM ARNs. Find it in: AWS Console → top-right account menu."
  type        = string
  # No default — this MUST be provided. Each AWS account is unique.
  # Terraform will prompt for it at apply time if not set.
}

# ── Project metadata ──────────────────────────────────────────

variable "project_name" {
  description = "Short name used as a prefix for all resource names (e.g., ECS cluster, ALB). Keeps resources identifiable when you have multiple projects in one account."
  type        = string
  default     = "ai-platform"
}

variable "environment" {
  description = "Deployment environment label. Attached as a tag to all resources for cost tracking and filtering. Examples: dev, staging, prod."
  type        = string
  default     = "dev"
}

# ── Networking variables ──────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC. /16 gives 65,536 IP addresses — far more than needed but AWS best practice for room to grow. 10.0.0.0/16 is the most common choice."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr_az1" {
  description = "CIDR for the first public subnet in us-east-1a. /24 = 256 IPs. Must be a subset of vpc_cidr."
  type        = string
  default     = "10.0.1.0/24"
}

variable "public_subnet_cidr_az2" {
  description = "CIDR for the second public subnet in us-east-1b. Having two subnets across two AZs enables high availability — if one AZ fails, traffic routes to the other."
  type        = string
  default     = "10.0.2.0/24"
}

# ── Container image URIs ──────────────────────────────────────
# These come from ECR after running push_images.sh.
# Pattern: <account_id>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>

variable "api_image_uri" {
  description = "Full ECR URI for the FastAPI backend image. Example: 123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-platform-api:latest"
  type        = string
  # No default — must be set after pushing image to ECR.
}

variable "ui_image_uri" {
  description = "Full ECR URI for the Streamlit frontend image. Example: 123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-platform-ui:latest"
  type        = string
  # No default — must be set after pushing image to ECR.
}

# ── ECS Task sizing variables ─────────────────────────────────
# Fargate pricing is per vCPU-second + GB-second.
# CPU is in "units" where 1024 units = 1 vCPU.
# Memory is in MB.
# Valid Fargate combinations: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#task_size

variable "api_cpu" {
  description = "CPU units for the API task. 512 = 0.5 vCPU. Valid values: 256, 512, 1024, 2048, 4096. More CPU = faster inference, higher cost."
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Memory in MB for the API task. 1024 = 1 GB. Must be compatible with cpu setting. At 512 CPU, valid memory: 1024-4096 MB."
  type        = number
  default     = 1024
}

variable "ui_cpu" {
  description = "CPU units for the Streamlit UI task. 256 = 0.25 vCPU. UI is lightweight — just serving web pages and forwarding requests."
  type        = number
  default     = 256
}

variable "ui_memory" {
  description = "Memory in MB for the Streamlit UI task. 512 = 0.5 GB. Streamlit is Python but doesn't need much memory for our use case."
  type        = number
  default     = 512
}

variable "api_desired_count" {
  description = "Number of API task instances to run. 1 for dev/learning. Set to 2+ for production high-availability. Each instance costs money."
  type        = number
  default     = 1
}

variable "ui_desired_count" {
  description = "Number of UI task instances to run. 1 for dev/learning. The ALB load-balances across all running instances automatically."
  type        = number
  default     = 1
}

# ── Application configuration ─────────────────────────────────

variable "cloud_mode" {
  description = "When true, the API returns a message directing users to configure an LLM API key instead of trying to reach Ollama (which isn't available in cloud). Set to false only if you configure an external LLM endpoint."
  type        = bool
  default     = true
}

variable "openai_api_key" {
  description = "Optional OpenAI API key. If provided, the API will use OpenAI instead of returning the cloud-mode placeholder message. Leave empty to use cloud-mode fallback."
  type        = string
  default     = ""
  sensitive   = true  # Marks this as sensitive — Terraform won't print it in logs
}
