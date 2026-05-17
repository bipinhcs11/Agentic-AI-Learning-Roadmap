#!/bin/bash
# ============================================================
# deploy.sh
#
# WHAT: Master deployment script. Runs all steps needed to
#       take the AI platform from local Docker images to a
#       fully running AWS ECS deployment.
#
# WHY:  Deployment has multiple steps across different tools
#       (AWS CLI, Docker, Terraform). Doing them manually means
#       remembering the order, the flags, the variables — and
#       making mistakes. This script automates the entire flow
#       with clear progress output and stops on any error.
#
# STEPS:
#   1. Check prerequisites (aws, docker, terraform)
#   2. Create ECR repositories
#   3. Build and push Docker images
#   4. Run Terraform to create all AWS infrastructure
#   5. Print the live URL
#
# USAGE:
#   bash deploy.sh
#   # Or with custom region:
#   AWS_REGION=us-west-2 bash deploy.sh
#
# COST WARNING:
#   Running this script creates real AWS resources that cost money.
#   Run teardown.sh when done to avoid unexpected charges.
#   Estimated cost: ~$1.50/day for this configuration.
# ============================================================

set -euo pipefail
# -e: exit on any error
# -u: treat unset variables as errors (catches typos)
# -o pipefail: pipe failure propagates (not just last command)

# ── Script location — all paths relative to this script ───────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="${SCRIPT_DIR}/infrastructure"

# ── ANSI color codes ───────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'  # Reset

# ── Configuration (override via environment variables) ─────────
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-ai-platform}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

# ── Helper functions ───────────────────────────────────────────

print_banner() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     AI Platform — AWS ECS Fargate Deploy     ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    local step="$1"
    local total="$2"
    local desc="$3"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Step ${step}/${total}: ${desc}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

print_error() {
    echo -e "${RED}  ✗ ERROR: $1${NC}"
}

print_info() {
    echo -e "${CYAN}  → $1${NC}"
}

check_command() {
    local cmd="$1"
    local install_hint="$2"
    if ! command -v "$cmd" &>/dev/null; then
        print_error "${cmd} is not installed."
        echo "    Install: ${install_hint}"
        return 1
    fi
    local version
    version=$("$cmd" --version 2>&1 | head -1)
    print_success "${cmd}: ${version}"
    return 0
}

# ── Main deployment flow ───────────────────────────────────────

print_banner

echo -e "${YELLOW}  Region:      ${AWS_REGION}${NC}"
echo -e "${YELLOW}  Project:     ${PROJECT_NAME}${NC}"
echo -e "${YELLOW}  Environment: ${ENVIRONMENT}${NC}"
echo ""
echo -e "${RED}  COST WARNING: This creates real AWS resources.${NC}"
echo -e "${RED}  Run teardown.sh when done to avoid charges.${NC}"
echo ""

# Prompt for confirmation before spending money
read -p "  Continue with deployment? [y/N] " -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "  Deployment cancelled."
    exit 0
fi

# ═══════════════════════════════════════════════════════════
# STEP 1: Check Prerequisites
# ═══════════════════════════════════════════════════════════
print_step 1 5 "Checking Prerequisites"

PREREQS_OK=true

# Check AWS CLI
# The AWS CLI talks to AWS APIs. Version 2 is required (version 1 has
# different syntax for some commands, especially ECR login).
if ! check_command "aws" "https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"; then
    PREREQS_OK=false
fi

# Check Docker
# Required to build and push images. Docker Desktop must be running.
if ! check_command "docker" "https://docs.docker.com/get-docker/"; then
    PREREQS_OK=false
fi

# Check Terraform
# Infrastructure as code tool. Version >= 1.5 required.
if ! check_command "terraform" "https://developer.hashicorp.com/terraform/install"; then
    PREREQS_OK=false
fi

# Check Python3 (used in ecr_setup.sh for JSON parsing)
if ! check_command "python3" "brew install python3 (or https://python.org)"; then
    PREREQS_OK=false
fi

if [[ "$PREREQS_OK" == "false" ]]; then
    echo ""
    print_error "One or more prerequisites are missing. Install them and retry."
    exit 1
fi

# Verify Docker daemon is running
if ! docker info &>/dev/null; then
    print_error "Docker daemon is not running. Start Docker Desktop."
    exit 1
fi
print_success "Docker daemon is running"

# Verify AWS credentials work
if ! AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null); then
    print_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi
print_success "AWS credentials valid (Account: ${AWS_ACCOUNT_ID})"

# Export for use in child scripts
export AWS_REGION
export AWS_ACCOUNT_ID

# ═══════════════════════════════════════════════════════════
# STEP 2: Create ECR Repositories
# ═══════════════════════════════════════════════════════════
print_step 2 5 "Creating ECR Repositories"

print_info "Running ecr_setup.sh..."
bash "${INFRA_DIR}/ecr_setup.sh"

# Load the ECR URIs written by ecr_setup.sh
ECR_ENV_FILE="${SCRIPT_DIR}/.ecr_env"
if [[ ! -f "$ECR_ENV_FILE" ]]; then
    print_error ".ecr_env not created by ecr_setup.sh. Check for errors above."
    exit 1
fi
source "$ECR_ENV_FILE"

print_success "ECR repositories ready"
print_info "API repo: ${API_REPO_URI}"
print_info "UI repo:  ${UI_REPO_URI}"

# ═══════════════════════════════════════════════════════════
# STEP 3: Build and Push Docker Images
# ═══════════════════════════════════════════════════════════
print_step 3 5 "Building and Pushing Docker Images"

print_info "Building for linux/amd64 (ECS runs on x86, not arm64)..."
print_info "This may take 5-10 minutes on first build..."

bash "${INFRA_DIR}/push_images.sh"

print_success "Images pushed to ECR"

# ═══════════════════════════════════════════════════════════
# STEP 4: Terraform — Create AWS Infrastructure
# ═══════════════════════════════════════════════════════════
print_step 4 5 "Deploying AWS Infrastructure with Terraform"

cd "${INFRA_DIR}"

# Write terraform.tfvars with the values from this deployment.
# terraform.tfvars is auto-loaded by Terraform — no need to pass
# -var flags on every command. Do NOT commit this file to git.
print_info "Writing terraform.tfvars..."
cat > terraform.tfvars <<EOF
# Auto-generated by deploy.sh — do not edit manually
# Regenerated on each deploy run.
aws_region     = "${AWS_REGION}"
aws_account_id = "${AWS_ACCOUNT_ID}"
api_image_uri  = "${API_REPO_URI}:latest"
ui_image_uri   = "${UI_REPO_URI}:latest"
project_name   = "${PROJECT_NAME}"
environment    = "${ENVIRONMENT}"
cloud_mode     = true
EOF

print_success "terraform.tfvars written"

# 4a. Terraform Init
# Downloads the AWS provider plugin (~50 MB) and sets up the
# .terraform directory with provider binaries.
# Safe to run multiple times — idempotent.
print_info "Running terraform init..."
terraform init -upgrade

# 4b. Terraform Plan
# Shows exactly what Terraform will create/modify/destroy.
# ALWAYS review the plan before apply. This is your last chance
# to catch mistakes before they cost money.
print_info "Running terraform plan..."
terraform plan -out=tfplan
# -out=tfplan: saves the plan to a file so 'apply' uses the exact
# same plan. Without -out, apply re-plans which could differ if
# state changed between plan and apply.

echo ""
echo -e "${YELLOW}  Review the plan above. Terraform will create ~20 resources.${NC}"
echo -e "${YELLOW}  This will take approximately 5-10 minutes.${NC}"
read -p "  Apply the Terraform plan? [y/N] " -r APPLY_CONFIRM
if [[ ! "$APPLY_CONFIRM" =~ ^[Yy]$ ]]; then
    echo "  Apply cancelled. Plan saved to ${INFRA_DIR}/tfplan"
    echo "  To apply later: cd infrastructure && terraform apply tfplan"
    exit 0
fi

# 4c. Terraform Apply
# Creates all the AWS resources in the plan.
# ECS service creation waits for tasks to be healthy, so this
# takes several minutes (usually 5-8 minutes).
print_info "Running terraform apply..."
print_info "This will take 5-10 minutes as ECS tasks start and health checks pass..."

terraform apply tfplan

print_success "Terraform apply complete"

# ═══════════════════════════════════════════════════════════
# STEP 5: Print Results
# ═══════════════════════════════════════════════════════════
print_step 5 5 "Deployment Complete"

# Extract outputs from Terraform state
ALB_URL=$(terraform output -raw alb_dns_name 2>/dev/null || echo "check terraform output")
API_LOG_GROUP=$(terraform output -raw api_log_group 2>/dev/null || echo "/ecs/ai-platform/api")
UI_LOG_GROUP=$(terraform output -raw ui_log_group 2>/dev/null || echo "/ecs/ai-platform/ui")
ECS_CLUSTER=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "${PROJECT_NAME}-cluster")

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Deployment Successful!               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}  Access your AI Platform:${NC}"
echo -e "  ${CYAN}${ALB_URL}${NC}"
echo ""
echo -e "${BOLD}  API Documentation:${NC}"
echo -e "  ${CYAN}${ALB_URL}/api/docs${NC}"
echo ""
echo -e "${BOLD}  View Logs (AWS CLI):${NC}"
echo "  aws logs tail ${API_LOG_GROUP} --follow"
echo "  aws logs tail ${UI_LOG_GROUP} --follow"
echo ""
echo -e "${BOLD}  View Logs (AWS Console):${NC}"
echo "  https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups"
echo ""
echo -e "${BOLD}  ECS Console:${NC}"
echo "  https://console.aws.amazon.com/ecs/v2/clusters/${ECS_CLUSTER}/services?region=${AWS_REGION}"
echo ""
echo -e "${RED}  IMPORTANT: Run teardown.sh when done to avoid ongoing charges!${NC}"
echo -e "${RED}  Estimated cost: ~\$1.50/day while running.${NC}"
echo ""

# Clean up the saved plan file (it's been applied)
rm -f tfplan

cd "${SCRIPT_DIR}"
