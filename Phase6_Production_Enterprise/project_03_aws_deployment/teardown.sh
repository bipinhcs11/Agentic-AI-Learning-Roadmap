#!/bin/bash
# ============================================================
# teardown.sh
#
# WHAT: Destroys ALL AWS resources created by this project to
#       stop incurring AWS charges.
#
# WHY:  AWS charges by the second for running resources. An ALB
#       alone costs ~$0.60/day even with zero traffic. ECS tasks
#       add ~$0.90/day. Leaving resources running overnight or
#       over a weekend adds up fast. Always tear down when done.
#
# WHAT GETS DELETED:
#   - ECS Services (API and UI)
#   - ECS Task Definitions (deregistered)
#   - ECS Cluster
#   - Application Load Balancer + Target Groups + Listener
#   - VPC + Subnets + Internet Gateway + Route Tables
#   - Security Groups
#   - IAM Roles + Policies
#   - CloudWatch Log Groups (and all logs inside them)
#
# WHAT IS NOT DELETED:
#   - ECR repositories and images (storage is cheap, ~$0.10/GB/month)
#   - Your local terraform.tfstate file (keeps the record of what was destroyed)
#   - Your local .ecr_env file
#
# USAGE:
#   bash teardown.sh
#
# SAFETY: This script requires double confirmation before destroying.
#         Terraform destroy also shows what will be deleted before acting.
# ============================================================

set -euo pipefail

# ── Script location ────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="${SCRIPT_DIR}/infrastructure"

# ── ANSI colors ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Banner ─────────────────────────────────────────────────────
echo ""
echo -e "${RED}╔══════════════════════════════════════════════╗${NC}"
echo -e "${RED}║        AI Platform — AWS TEARDOWN            ║${NC}"
echo -e "${RED}║        This will delete ALL resources        ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Verify Terraform state exists ─────────────────────────────
# If there's no state file, Terraform doesn't know what it created
# and can't destroy anything. This would happen if you ran teardown
# from a different machine or deleted the state file.
if [[ ! -f "${INFRA_DIR}/terraform.tfstate" ]]; then
    echo -e "${RED}ERROR: No terraform.tfstate found in ${INFRA_DIR}${NC}"
    echo ""
    echo "Possible causes:"
    echo "  1. You never ran deploy.sh on this machine"
    echo "  2. The state file was deleted"
    echo "  3. You're in the wrong directory"
    echo ""
    echo "If resources are still running in AWS, destroy them manually:"
    echo "  AWS Console → ECS → Clusters → delete cluster"
    echo "  AWS Console → EC2 → Load Balancers → delete ALB"
    echo "  AWS Console → VPC → Your VPCs → delete VPC"
    exit 1
fi

# ── Load configuration ─────────────────────────────────────────
AWS_REGION="${AWS_REGION:-us-east-1}"

# Load ECR env if it exists (not required for destroy but nice to show)
ECR_ENV_FILE="${SCRIPT_DIR}/.ecr_env"
if [[ -f "$ECR_ENV_FILE" ]]; then
    source "$ECR_ENV_FILE"
fi

# ── Show what will be destroyed ────────────────────────────────
echo -e "${YELLOW}The following AWS resources will be PERMANENTLY DELETED:${NC}"
echo ""
echo "  • ECS Cluster and all services (API + UI tasks will be stopped)"
echo "  • Application Load Balancer (your app URL will stop working)"
echo "  • VPC, subnets, internet gateway, route tables, security groups"
echo "  • IAM roles created for ECS"
echo "  • CloudWatch log groups (ALL LOGS WILL BE DELETED)"
echo ""
echo -e "${CYAN}ECR repositories are NOT deleted (cheap to keep, images preserved).${NC}"
echo ""

# ── First confirmation ─────────────────────────────────────────
echo -e "${RED}${BOLD}WARNING: This action CANNOT be undone.${NC}"
echo -e "${RED}All AWS resources and their data will be permanently deleted.${NC}"
echo ""
read -p "  Are you sure you want to destroy all resources? [y/N] " -r CONFIRM_1
if [[ ! "$CONFIRM_1" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${GREEN}  Teardown cancelled. Resources are still running.${NC}"
    exit 0
fi

# ── Second confirmation (type the word) ───────────────────────
# Require typing a specific word to prevent accidental confirmation.
# This is a common safety pattern for destructive operations.
echo ""
echo -e "${RED}  FINAL CONFIRMATION REQUIRED${NC}"
read -p "  Type 'destroy' to confirm: " -r CONFIRM_2
if [[ "$CONFIRM_2" != "destroy" ]]; then
    echo ""
    echo -e "${GREEN}  Teardown cancelled. You typed '${CONFIRM_2}', not 'destroy'.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}  Proceeding with teardown...${NC}"
echo ""

# ── Run Terraform Destroy ──────────────────────────────────────
cd "${INFRA_DIR}"

# terraform destroy shows a plan of what will be destroyed,
# then asks for confirmation AGAIN (we pass -auto-approve to
# skip that since we already confirmed above).
#
# The destroy order matters — Terraform handles dependencies:
# ECS Services → ECS Tasks → ALB → Target Groups → Security Groups
# → Subnets → IGW → Route Tables → VPC → IAM Roles
# Terraform figures out the correct order automatically.
echo -e "${YELLOW}Running terraform destroy...${NC}"
echo -e "${CYAN}(This takes 3-8 minutes as AWS cleans up resources)${NC}"
echo ""

terraform destroy -auto-approve

DESTROY_EXIT_CODE=$?

if [[ $DESTROY_EXIT_CODE -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║        Teardown Complete                     ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}  All AWS resources have been destroyed.${NC}"
    echo -e "${GREEN}  AWS billing for these resources will stop shortly.${NC}"
    echo ""
    echo "  Verify in AWS Console:"
    echo "  https://console.aws.amazon.com/ecs/v2?region=${AWS_REGION}"
    echo "  https://console.aws.amazon.com/ec2/v2/home?region=${AWS_REGION}#LoadBalancers:"
    echo ""
    echo "  ECR repositories still exist (minimal cost):"
    echo "  https://console.aws.amazon.com/ecr/repositories?region=${AWS_REGION}"
    echo ""
    echo "  To redeploy later: bash deploy.sh"
    echo ""

    # Clean up generated files that are no longer valid
    rm -f "${INFRA_DIR}/terraform.tfvars"
    rm -f "${SCRIPT_DIR}/.ecr_env"
    echo -e "${CYAN}  Cleaned up: terraform.tfvars and .ecr_env${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}  Terraform destroy encountered errors (exit code: ${DESTROY_EXIT_CODE}).${NC}"
    echo ""
    echo "  Some resources may not have been deleted. Check:"
    echo "  1. AWS Console for any remaining resources"
    echo "  2. Run 'terraform destroy' again manually from infrastructure/"
    echo "  3. Check if any resources have deletion protection enabled"
    echo ""
    echo "  Manual cleanup order:"
    echo "    aws ecs update-service --cluster ai-platform-cluster --service ai-platform-api-service --desired-count 0 --region ${AWS_REGION}"
    echo "    aws ecs update-service --cluster ai-platform-cluster --service ai-platform-ui-service --desired-count 0 --region ${AWS_REGION}"
    echo "    Then wait 1 minute, then: terraform destroy -auto-approve"
    exit 1
fi

cd "${SCRIPT_DIR}"
