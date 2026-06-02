# ═══════════════════════════════════════════════════════════════
# Phase 6 Project 03 — Architecture Diagram Generator
# Uses the `diagrams` library with official AWS service logos
# Run: python generate_diagram.py
# Output: architecture.png (same directory)
# ═══════════════════════════════════════════════════════════════

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import ECS, ECR
from diagrams.aws.network import ALB, InternetGateway, VPC
from diagrams.aws.management import Cloudwatch
from diagrams.aws.security import IAM
from diagrams.onprem.client import Users

diagram_attrs = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.8",
    "splines": "ortho",
    "nodesep": "0.8",
    "ranksep": "1.2",
}

output_path = "/Users/bipinpradhan/Documents/Agentic AI learning Roadmap/Phase6_Production_Enterprise/project_03_aws_deployment/architecture"

with Diagram(
    "Phase 6 — AWS ECS Fargate Deployment\nai-platform (us-east-1)",
    filename=output_path,
    outformat="png",
    graph_attr=diagram_attrs,
    show=False,
):
    user = Users("Browser / curl")

    with Cluster("AWS Cloud — us-east-1"):

        igw = InternetGateway("Internet Gateway")

        with Cluster("VPC  10.0.0.0/16"):

            alb = ALB("Application Load Balancer\nai-platform-alb\nport 80  (internet-facing)")

            with Cluster("Availability Zone us-east-1a\nSubnet 10.0.1.0/24"):
                api_task_a = ECS("ECS Fargate Task\nFastAPI  :8000\n0.5 vCPU · 1 GB")

            with Cluster("Availability Zone us-east-1b\nSubnet 10.0.2.0/24"):
                ui_task_b = ECS("ECS Fargate Task\nStreamlit  :8501\n0.25 vCPU · 0.5 GB")

        with Cluster("Container Registry"):
            ecr = ECR("ECR\nai-platform-api:latest\nai-platform-ui:latest")

        with Cluster("Observability"):
            cw = Cloudwatch("CloudWatch Logs\n/ecs/ai-platform/api\n/ecs/ai-platform/ui")

        iam = IAM("IAM Roles\nExecution Role\nTask Role")

    # Traffic flow
    user >> Edge(label="HTTP :80") >> igw
    igw >> alb
    alb >> Edge(label="/api/*") >> api_task_a
    alb >> Edge(label="/* (default)") >> ui_task_b

    # ECR pulls on deploy
    ecr >> Edge(label="docker pull", style="dashed") >> api_task_a
    ecr >> Edge(label="docker pull", style="dashed") >> ui_task_b

    # Logs
    api_task_a >> Edge(label="stdout/stderr", style="dashed") >> cw
    ui_task_b  >> Edge(label="stdout/stderr", style="dashed") >> cw

    # IAM
    iam >> Edge(style="dashed") >> api_task_a
