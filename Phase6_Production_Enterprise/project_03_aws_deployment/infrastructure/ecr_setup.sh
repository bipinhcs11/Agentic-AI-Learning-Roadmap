#!/bin/bash
# ============================================================
# infrastructure/ecr_setup.sh
#
# WHAT: Creates two Amazon ECR (Elastic Container Registry)
#       repositories for our AI platform Docker images.
#
# WHY:  ECR is AWS's private Docker registry — think of it as
#       DockerHub but private, inside your AWS account. ECS
#       (Elastic Container Service) needs images stored in ECR
#       because public DockerHub has rate limits and ECS needs
#       fast, same-region image pulls.
#
#       We create TWO repos:
#         - ai-platform-api  → FastAPI backend
#         - ai-platform-ui   → Streamlit frontend
#
# USAGE: bash infrastructure/ecr_setup.sh
# ============================================================

set -euo pipefail
# set -e  → exit immediately if any command fails
# set -u  → treat unset variables as errors
# set -o pipefail → if a pipe fails, the whole command fails

# ── ANSI color codes for readable output ──────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'  # No Color / reset

# ── Configuration ─────────────────────────────────────────────
# These values can be overridden by environment variables.
# Default region is us-east-1 — change if your AWS account
# default is different (e.g., ap-southeast-1 for Singapore).
AWS_REGION="${AWS_REGION:-us-east-1}"

# Repository names — these become the ECR repo names.
# Full image URI pattern: <account_id>.dkr.ecr.<region>.amazonaws.com/<repo_name>:<tag>
API_REPO_NAME="ai-platform-api"
UI_REPO_NAME="ai-platform-ui"

echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${BLUE}  ECR Repository Setup — AI Platform      ${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo ""

# ── Step 1: Verify AWS CLI is installed ───────────────────────
# The AWS CLI is the command-line tool for talking to AWS APIs.
# Without it, none of the aws commands below will work.
echo -e "${YELLOW}[1/4] Checking AWS CLI installation...${NC}"

if ! command -v aws &>/dev/null; then
    echo -e "${RED}ERROR: AWS CLI not found.${NC}"
    echo "Install it from: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    echo "Then run: aws configure"
    exit 1
fi

AWS_CLI_VERSION=$(aws --version 2>&1 | cut -d' ' -f1)
echo -e "${GREEN}  ✓ Found: ${AWS_CLI_VERSION}${NC}"

# ── Step 2: Verify AWS CLI is configured with credentials ─────
# 'aws sts get-caller-identity' is the canonical "am I logged in?"
# check. It returns your AWS account ID, user/role ARN, and user ID.
# If credentials aren't configured, this command will fail with
# an auth error, and set -e will stop the script.
echo -e "${YELLOW}[2/4] Verifying AWS credentials...${NC}"

CALLER_IDENTITY=$(aws sts get-caller-identity --output json 2>&1) || {
    echo -e "${RED}ERROR: AWS credentials not configured or invalid.${NC}"
    echo "Run 'aws configure' and provide your Access Key ID + Secret."
    echo "Or set AWS_PROFILE environment variable to a named profile."
    exit 1
}

# Parse the account ID from the JSON response.
# We use this to construct image URIs like:
#   123456789012.dkr.ecr.us-east-1.amazonaws.com/ai-platform-api:latest
AWS_ACCOUNT_ID=$(echo "$CALLER_IDENTITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['Account'])")
CALLER_ARN=$(echo "$CALLER_IDENTITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['Arn'])")

echo -e "${GREEN}  ✓ Account ID: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${GREEN}  ✓ Identity:   ${CALLER_ARN}${NC}"
echo -e "${GREEN}  ✓ Region:     ${AWS_REGION}${NC}"

# ── Step 3: Create ECR repositories ───────────────────────────
# ECR repositories are like "folders" in your private registry.
# Each image name gets its own repository.
#
# --image-scanning-configuration scanOnPush=true
#   → ECR will automatically scan images for OS/library CVEs
#     (Common Vulnerabilities and Exposures) when you push.
#     Free basic scanning, useful for production.
#
# --encryption-configuration encryptionType=AES256
#   → Images are encrypted at rest using AWS-managed keys.
#     No extra cost. Always worth enabling.
echo -e "${YELLOW}[3/4] Creating ECR repositories...${NC}"

create_ecr_repo() {
    local REPO_NAME="$1"

    # Check if the repo already exists. If it does, skip creation.
    # This makes the script idempotent (safe to run multiple times).
    if aws ecr describe-repositories \
        --repository-names "$REPO_NAME" \
        --region "$AWS_REGION" &>/dev/null; then
        echo -e "${CYAN}  → Repository '${REPO_NAME}' already exists — skipping creation.${NC}"
    else
        # Create the repository
        aws ecr create-repository \
            --repository-name "$REPO_NAME" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256 \
            --output json > /dev/null

        echo -e "${GREEN}  ✓ Created repository: ${REPO_NAME}${NC}"
    fi

    # Retrieve and print the repository URI regardless of whether
    # we just created it or it already existed.
    REPO_URI=$(aws ecr describe-repositories \
        --repository-names "$REPO_NAME" \
        --region "$AWS_REGION" \
        --query 'repositories[0].repositoryUri' \
        --output text)

    echo -e "${GREEN}    URI: ${REPO_URI}${NC}"
    # Export so the calling script can capture it
    echo "$REPO_URI"
}

echo ""
echo "  Creating API repository..."
API_REPO_URI=$(create_ecr_repo "$API_REPO_NAME" | tail -1)

echo ""
echo "  Creating UI repository..."
UI_REPO_URI=$(create_ecr_repo "$UI_REPO_NAME" | tail -1)

# ── Step 4: Print summary ──────────────────────────────────────
echo ""
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ECR Setup Complete!${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo ""
echo "  Save these URIs — you'll need them for push_images.sh"
echo "  and for Terraform variables:"
echo ""
echo -e "  ${CYAN}API Image URI:${NC}"
echo "    ${API_REPO_URI}:latest"
echo ""
echo -e "  ${CYAN}UI Image URI:${NC}"
echo "    ${UI_REPO_URI}:latest"
echo ""
echo "  To use in push_images.sh, set:"
echo "    export AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}"
echo "    export AWS_REGION=${AWS_REGION}"
echo ""

# Write URIs to a .env file for use by other scripts.
# This avoids copy-paste errors when chaining scripts together.
ENV_FILE="$(dirname "$0")/../.ecr_env"
cat > "$ENV_FILE" <<EOF
# Auto-generated by ecr_setup.sh — do not edit manually
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
AWS_REGION=${AWS_REGION}
API_REPO_URI=${API_REPO_URI}
UI_REPO_URI=${UI_REPO_URI}
EOF

echo -e "  ${CYAN}URIs saved to .ecr_env for use by other scripts.${NC}"
echo ""
