# ============================================================
# infrastructure/outputs.tf
#
# WHAT: Declares the values Terraform will print after a
#       successful 'terraform apply'. Also makes these values
#       available to other Terraform configurations via
#       'terraform_remote_state' data sources.
#
# WHY:  After Terraform creates 50+ resources, you need to
#       quickly find the important ones — the URL to access
#       your app, the cluster name for debugging, ECR URIs
#       for re-pushing images. Outputs surface exactly that.
#
#       Think of outputs as Terraform's "return values".
# ============================================================

# ── Access URL ────────────────────────────────────────────────
# The Application Load Balancer DNS name is the public URL
# where your app is reachable. It looks like:
#   ai-platform-alb-1234567890.us-east-1.elb.amazonaws.com
# AWS automatically creates this DNS record when you create an ALB.
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer — use this URL to access the deployed AI platform. Prefix with http:// in your browser."
  value       = "http://${aws_lb.main.dns_name}"
}

output "api_url" {
  description = "Direct URL to the FastAPI backend. The ALB routes /api/* to this service. Access the interactive API docs at /api/docs"
  value       = "http://${aws_lb.main.dns_name}/api/docs"
}

output "ui_url" {
  description = "Direct URL to the Streamlit UI frontend served through the ALB."
  value       = "http://${aws_lb.main.dns_name}/"
}

# ── ECS cluster information ───────────────────────────────────
output "ecs_cluster_name" {
  description = "Name of the ECS cluster. Use this with the AWS CLI to inspect running tasks: aws ecs list-tasks --cluster <name>"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "Full ARN of the ECS cluster. ARNs (Amazon Resource Names) are globally unique identifiers for AWS resources. Format: arn:aws:ecs:<region>:<account>:cluster/<name>"
  value       = aws_ecs_cluster.main.arn
}

output "api_service_name" {
  description = "Name of the ECS service running the API tasks. Use with: aws ecs describe-services --cluster <cluster> --services <name>"
  value       = aws_ecs_service.api.name
}

output "ui_service_name" {
  description = "Name of the ECS service running the UI tasks."
  value       = aws_ecs_service.ui.name
}

# ── ECR repository information ────────────────────────────────
# ECR registry URL pattern: <account>.dkr.ecr.<region>.amazonaws.com/<repo>
output "ecr_api_repository_url" {
  description = "ECR repository URL for the API image. Use this as api_image_uri when re-running Terraform after updating images."
  value       = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/ai-platform-api"
}

output "ecr_ui_repository_url" {
  description = "ECR repository URL for the UI image."
  value       = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/ai-platform-ui"
}

# ── Networking information ────────────────────────────────────
output "vpc_id" {
  description = "ID of the VPC created for this deployment. Use to find associated subnets, security groups, and routing tables in the AWS Console."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs. The ECS tasks and ALB run in these subnets. They're 'public' because they have a route to the Internet Gateway."
  value       = [aws_subnet.public_az1.id, aws_subnet.public_az2.id]
}

# ── CloudWatch log groups ─────────────────────────────────────
output "api_log_group" {
  description = "CloudWatch log group name for API container logs. View logs: aws logs tail <log-group> --follow"
  value       = aws_cloudwatch_log_group.api.name
}

output "ui_log_group" {
  description = "CloudWatch log group name for UI container logs."
  value       = aws_cloudwatch_log_group.ui.name
}

# ── Cost reminder ─────────────────────────────────────────────
output "cost_reminder" {
  description = "Estimated monthly cost breakdown for this deployment."
  value       = <<-EOT
    Estimated AWS costs (us-east-1, on-demand pricing):
      ECS Fargate API  (0.5 vCPU, 1 GB, 1 task) : ~$14/month
      ECS Fargate UI   (0.25 vCPU, 0.5 GB, 1 task) : ~$5/month
      ALB              (1 ALB + LCU hours)          : ~$18/month
      ECR storage      (<1 GB images)               : ~$0.10/month
      CloudWatch logs  (<1 GB)                      : ~$0.50/month
      Data transfer    (varies)                     : ~$1-5/month
      ─────────────────────────────────────────────────────────
      TOTAL ESTIMATE                                : ~$38-42/month
    Run teardown.sh when done learning to avoid charges!
  EOT
}
