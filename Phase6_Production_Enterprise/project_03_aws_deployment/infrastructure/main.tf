# ============================================================
# infrastructure/main.tf
#
# WHAT: Complete AWS infrastructure for deploying the AI
#       platform using ECS Fargate, an Application Load
#       Balancer, and supporting networking resources.
#
# WHY:  Instead of clicking through the AWS Console (slow,
#       error-prone, non-reproducible), Terraform declares
#       infrastructure as code. Run 'terraform apply' and the
#       entire stack is created in ~5 minutes. Run 'terraform
#       destroy' and it's all cleaned up. No orphaned resources,
#       no forgotten running instances costing money overnight.
#
# ARCHITECTURE:
#
#   Internet
#      │
#      ▼
#   [ALB - Application Load Balancer]   ← single public endpoint
#      │
#      ├─── /api/* ──► [ECS Task: FastAPI]   (0.5 vCPU, 1 GB)
#      │                   port 8000
#      │
#      └─── /* ──────► [ECS Task: Streamlit] (0.25 vCPU, 0.5 GB)
#                          port 8501
#
#   All running inside a VPC (isolated network),
#   across 2 Availability Zones for resilience.
#
# TERRAFORM STATE:
#   This config uses LOCAL state (terraform.tfstate file).
#   For a team or production, you'd use S3 + DynamoDB for
#   shared, locked state. We keep it simple for learning.
#
# ============================================================

# ── Terraform version constraints ────────────────────────────
# Pins minimum versions to avoid breaking changes in future releases.
# The AWS provider releases frequently — this prevents auto-upgrade surprises.
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # ~> means "5.x but not 6.x" — patch and minor updates OK
    }
  }

  # LOCAL STATE — no backend block = local state file.
  # The terraform.tfstate file in infrastructure/ tracks everything Terraform created.
  # DO NOT delete this file or Terraform loses track of your resources.
  # DO NOT commit this file to git (add to .gitignore) — it can contain secrets.
}

# ── AWS Provider ──────────────────────────────────────────────
# The provider is the plugin that talks to the AWS API.
# It reads credentials from: environment variables, ~/.aws/credentials,
# or IAM instance profile (if running on EC2/Cloud9).
provider "aws" {
  region = var.aws_region

  # Default tags applied to EVERY resource Terraform creates.
  # This is critical for cost tracking — you can filter your AWS
  # Cost Explorer by tag to see exactly what this project costs.
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "agentic-ai-learning"
    }
  }
}

# ════════════════════════════════════════════════════════════
# NETWORKING LAYER
# ════════════════════════════════════════════════════════════
# A VPC (Virtual Private Cloud) is your private, isolated section
# of the AWS cloud. Think of it as your own data center network.
# Every resource (ECS tasks, ALB) lives inside the VPC.
# Nothing can reach your resources unless explicitly allowed.

# ── VPC ───────────────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr
  # cidr_block: the IP address range for your entire VPC.
  # 10.0.0.0/16 means IPs from 10.0.0.0 to 10.0.255.255 (65,536 addresses).

  enable_dns_hostnames = true
  # enable_dns_hostnames: AWS gives each EC2/ECS resource a DNS name
  # like ip-10-0-1-5.ec2.internal. Required for ECS service discovery.

  enable_dns_support = true
  # enable_dns_support: enables the AWS DNS resolver inside the VPC.
  # Without this, containers can't resolve DNS names (e.g., can't reach ECR).

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# ── Public Subnets ────────────────────────────────────────────
# A subnet is a subdivision of a VPC, tied to one Availability Zone.
# "Public" means it has a route to the Internet Gateway (the internet).
#
# WHY TWO SUBNETS? High availability. AWS guarantees each AZ is
# physically separate (different power, cooling, networking). If AZ-a
# goes down, your service continues in AZ-b. ALBs REQUIRE at least 2 AZs.

resource "aws_subnet" "public_az1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.public_subnet_cidr_az1  # 10.0.1.0/24 = 256 IPs
  availability_zone = "${var.aws_region}a"        # e.g., us-east-1a

  # map_public_ip_on_launch: any resource launched in this subnet
  # automatically gets a public IP. Needed for ECS tasks in public subnets
  # to pull images from ECR and communicate with AWS APIs.
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-az1"
    Type = "public"
  }
}

resource "aws_subnet" "public_az2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.public_subnet_cidr_az2  # 10.0.2.0/24 = 256 IPs
  availability_zone = "${var.aws_region}b"        # e.g., us-east-1b

  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-az2"
    Type = "public"
  }
}

# ── Internet Gateway ──────────────────────────────────────────
# The Internet Gateway (IGW) is the VPC's connection to the internet.
# Without it, nothing inside the VPC can reach the outside world
# (or be reached from it). One IGW per VPC.
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# ── Route Table ───────────────────────────────────────────────
# A route table is like a GPS for network packets — it tells packets
# where to go based on their destination IP.
#
# Rule: "for any IP address (0.0.0.0/0 = all traffic), send it to
# the Internet Gateway" — this is what makes subnets "public".
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"          # All internet traffic
    gateway_id = aws_internet_gateway.main.id  # Goes to the IGW
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# ── Route Table Associations ──────────────────────────────────
# Associates the public route table with each subnet.
# A subnet without a route table association uses the VPC's default
# route table (local-only traffic). We explicitly attach our public one.
resource "aws_route_table_association" "public_az1" {
  subnet_id      = aws_subnet.public_az1.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_az2" {
  subnet_id      = aws_subnet.public_az2.id
  route_table_id = aws_route_table.public.id
}

# ════════════════════════════════════════════════════════════
# SECURITY GROUPS
# ════════════════════════════════════════════════════════════
# Security Groups are stateful firewalls that control traffic
# to/from AWS resources. "Stateful" means if you allow outbound
# traffic, the return traffic is automatically allowed.
#
# PRINCIPLE OF LEAST PRIVILEGE: only allow exactly what's needed.
# The ECS tasks should NOT be directly reachable from the internet —
# all traffic must flow through the ALB.

# ── ALB Security Group ────────────────────────────────────────
# The ALB faces the internet, so it needs to accept HTTP traffic
# from anywhere (0.0.0.0/0 = all internet IPs).
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for the Application Load Balancer. Allows HTTP from internet."
  vpc_id      = aws_vpc.main.id

  # INBOUND: Accept HTTP traffic from the internet
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # All IPv4 internet
  }

  # INBOUND: Accept HTTPS traffic (for future SSL/TLS setup)
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # OUTBOUND: ALB needs to forward traffic to ECS tasks.
  # Allow all outbound so ALB can reach any port on ECS tasks.
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"  # -1 means all protocols
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# ── ECS Tasks Security Group ──────────────────────────────────
# ECS tasks should ONLY accept traffic FROM the ALB, not from the
# internet directly. We reference the ALB's security group rather
# than an IP range — this is more maintainable and precise.
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Security group for ECS tasks. Only accepts traffic from ALB."
  vpc_id      = aws_vpc.main.id

  # INBOUND: FastAPI on port 8000 — only from the ALB security group
  ingress {
    description     = "FastAPI from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]  # Only from ALB SG, not internet
  }

  # INBOUND: Streamlit on port 8501 — only from the ALB security group
  ingress {
    description     = "Streamlit from ALB"
    from_port       = 8501
    to_port         = 8501
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # OUTBOUND: ECS tasks need to reach the internet to:
  #   - Pull images from ECR (even though we're in the VPC, ECR uses HTTPS)
  #   - Call external APIs (Claude API, OpenAI, etc.)
  #   - Report logs to CloudWatch
  egress {
    description = "All outbound traffic for API calls and ECR pulls"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-tasks-sg"
  }
}

# ════════════════════════════════════════════════════════════
# APPLICATION LOAD BALANCER (ALB)
# ════════════════════════════════════════════════════════════
# The ALB is the single entry point for all traffic to your app.
# It sits in front of your ECS tasks and provides:
#   - Load balancing: distributes requests across multiple task instances
#   - Health checking: routes traffic only to healthy tasks
#   - Path-based routing: /api/* → API service, /* → UI service
#   - SSL termination: (with ACM cert) handles HTTPS in one place
#
# ALB vs NLB vs CLB:
#   ALB = Layer 7 (HTTP/HTTPS), path/host-based routing → use for web apps
#   NLB = Layer 4 (TCP/UDP), ultra-high performance → use for gaming/streaming
#   CLB = Legacy, don't use for new projects

resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false   # false = internet-facing (public IP)
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]

  # ALBs must span multiple subnets (multiple AZs) for resilience.
  # AWS runs two ALB nodes, one per AZ. If az1 fails, az2 keeps serving.
  subnets = [
    aws_subnet.public_az1.id,
    aws_subnet.public_az2.id
  ]

  # enable_deletion_protection: when true, you can't delete the ALB
  # without first disabling this flag. Good for production, annoying
  # in dev when you're iterating. Set false for learning.
  enable_deletion_protection = false

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# ── ALB Listener ──────────────────────────────────────────────
# The listener is the process that checks for incoming connection
# requests on a specific port. Think of it as the receptionist —
# it answers all calls on port 80 and decides where to route them.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  # Default action: if no path rules match, send to the UI.
  # This handles requests to "/" and anything not matched by the API rule.
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ui.arn
  }
}

# ── ALB Listener Rule — API routing ──────────────────────────
# Path-based routing rule: requests starting with /api go to the API service.
# The ALB evaluates rules in priority order (lower number = higher priority).
# Our API rule (priority 100) is checked before the default (UI) action.
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100  # Lower number = evaluated first

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/api"]  # Match /api and anything under /api/
    }
  }
}

# ── Target Groups ─────────────────────────────────────────────
# A Target Group is the ALB's list of backends to send traffic to.
# For ECS, targets are dynamically registered/deregistered as
# tasks start and stop. You don't manage this manually.
#
# Health checks: the ALB periodically sends a request to each target.
# If it fails, the ALB stops sending real traffic to that target.
# This is the core of zero-downtime deployments — new tasks are
# only added to rotation after health checks pass.

resource "aws_lb_target_group" "api" {
  name        = "${var.project_name}-api-tg"
  port        = 8000          # FastAPI listens on 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  # target_type = "ip" is required for ECS Fargate with awsvpc networking.
  # Each Fargate task gets its own IP; the ALB registers that IP directly.

  health_check {
    enabled             = true
    healthy_threshold   = 2     # 2 consecutive successes → healthy
    unhealthy_threshold = 3     # 3 consecutive failures → unhealthy
    timeout             = 5     # Seconds to wait for response
    interval            = 30    # Seconds between health checks
    path                = "/health"  # FastAPI should expose GET /health → 200
    matcher             = "200"      # 200 OK = healthy
    protocol            = "HTTP"
  }

  # Deregistration delay: when a task is stopping, wait this many seconds
  # before removing it from the target group. This allows in-flight requests
  # to complete gracefully (graceful shutdown).
  deregistration_delay = 30

  tags = {
    Name = "${var.project_name}-api-tg"
  }
}

resource "aws_lb_target_group" "ui" {
  name        = "${var.project_name}-ui-tg"
  port        = 8501          # Streamlit listens on 8501
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10    # Streamlit can be slower to respond on health check
    interval            = 30
    path                = "/_stcore/health"  # Streamlit's built-in health endpoint
    matcher             = "200"
    protocol            = "HTTP"
  }

  deregistration_delay = 30

  tags = {
    Name = "${var.project_name}-ui-tg"
  }
}

# ════════════════════════════════════════════════════════════
# IAM ROLES FOR ECS
# ════════════════════════════════════════════════════════════
# ECS needs two IAM roles:
#
# 1. TASK EXECUTION ROLE: used by the ECS AGENT (not your code)
#    to pull images from ECR and send logs to CloudWatch.
#    Your containers never use this role directly.
#
# 2. TASK ROLE: used BY YOUR CONTAINER CODE to call AWS APIs
#    (e.g., read from S3, send to SQS). If your app doesn't
#    call AWS APIs, you can skip this, but it's good practice.

# ── Task Execution Role ───────────────────────────────────────
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-execution-role"

  # Trust policy: who is allowed to assume this role.
  # "ecs-tasks.amazonaws.com" = the ECS service itself.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-execution-role"
  }
}

# Attach AWS's managed policy for ECS task execution.
# This policy grants:
#   - ecr:GetAuthorizationToken     → get ECR login token
#   - ecr:BatchGetImage             → pull image layers
#   - logs:CreateLogStream          → create log streams in CloudWatch
#   - logs:PutLogEvents             → write log entries
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ── Task Role ─────────────────────────────────────────────────
# Your application code runs with this role's permissions.
# For this learning project, we grant no extra AWS permissions —
# the app only needs to serve HTTP and call external APIs (Claude, OpenAI).
# In production, you'd add policies here for S3, DynamoDB, etc.
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task-role"
  }
}

# ════════════════════════════════════════════════════════════
# CLOUDWATCH LOG GROUPS
# ════════════════════════════════════════════════════════════
# CloudWatch Logs is AWS's logging service. ECS containers can't
# write logs to disk (Fargate is serverless — no persistent filesystem
# outside the container). Instead, the awslogs driver streams stdout/
# stderr from your containers to CloudWatch automatically.
#
# Log groups are namespaced collections of log streams.
# One log stream per ECS task instance.

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project_name}/api"
  # Convention: /ecs/<project>/<service> — easy to find in Console

  retention_in_days = 7
  # Keep logs for 7 days. CloudWatch charges per GB stored.
  # For learning: 7 days is plenty. Production: 30-90 days.
  # Options: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, etc.

  tags = {
    Name = "${var.project_name}-api-logs"
  }
}

resource "aws_cloudwatch_log_group" "ui" {
  name              = "/ecs/${var.project_name}/ui"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-ui-logs"
  }
}

# ════════════════════════════════════════════════════════════
# ECS CLUSTER
# ════════════════════════════════════════════════════════════
# An ECS Cluster is a logical grouping of ECS services and tasks.
# For Fargate, the cluster is mostly just a namespace — there are
# no EC2 instances to manage. AWS handles all the underlying
# servers. You just say "run this container" and it runs.
#
# EC2 launch type vs Fargate:
#   EC2:    YOU manage EC2 instances (patch, scale, monitor)
#   Fargate: AWS manages everything — you only pay per task second

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
    # Container Insights: enables detailed CloudWatch metrics for your
    # cluster — CPU%, memory%, network, disk for each task and service.
    # Slightly extra cost but extremely useful for debugging.
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# ════════════════════════════════════════════════════════════
# ECS TASK DEFINITIONS
# ════════════════════════════════════════════════════════════
# A Task Definition is the blueprint for running a container.
# Think of it as a docker-compose.yml for a single service —
# it specifies: which image, CPU/memory limits, environment
# variables, ports, logging config, and IAM roles.
#
# Task Definition versions: each time you update and register
# a task definition, ECS creates a new revision (e.g., :1, :2, :3).
# Services can be updated to use a new revision for zero-downtime deploys.

# ── API Task Definition ───────────────────────────────────────
resource "aws_ecs_task_definition" "api" {
  family = "${var.project_name}-api"
  # family: the base name for this task definition.
  # Full name will be: ai-platform-api:1, ai-platform-api:2, etc.

  requires_compatibilities = ["FARGATE"]
  # Fargate = serverless containers. No EC2 instances to manage.

  network_mode = "awsvpc"
  # awsvpc: each task gets its own Elastic Network Interface (ENI)
  # with its own private IP. Required for Fargate. Enables fine-grained
  # security group control at the task level (not just instance level).

  cpu    = var.api_cpu     # 512 = 0.5 vCPU
  memory = var.api_memory  # 1024 = 1 GB

  execution_role_arn = aws_iam_role.ecs_task_execution.arn
  # execution_role_arn: used by ECS agent to pull image, write logs.

  task_role_arn = aws_iam_role.ecs_task.arn
  # task_role_arn: used by your application code for AWS API calls.

  # container_definitions: JSON describing the containers in this task.
  # For this project, one container per task. Multi-container tasks
  # (sidecars) are useful for service meshes, log shippers, etc.
  container_definitions = jsonencode([
    {
      name  = "api"
      image = var.api_image_uri
      # The full ECR URI. ECS will pull this image using the execution role.

      essential = true
      # essential: if this container stops/crashes, the entire task stops.
      # For single-container tasks, always true.

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000  # In awsvpc mode, hostPort must equal containerPort
          protocol      = "tcp"
        }
      ]

      environment = [
        # CLOUD_MODE tells the API it's running on AWS, not locally.
        # When true, the API returns a friendly message instead of
        # trying to reach Ollama (which isn't available in cloud).
        {
          name  = "CLOUD_MODE"
          value = tostring(var.cloud_mode)
        },
        {
          name  = "HOST"
          value = "0.0.0.0"
          # FastAPI/uvicorn must bind to 0.0.0.0 (all interfaces),
          # not 127.0.0.1 (localhost only), to accept traffic from the ALB.
        },
        {
          name  = "PORT"
          value = "8000"
        },
        {
          name  = "LOG_LEVEL"
          value = "info"
        }
      ]

      # Secrets: sensitive values should come from AWS Secrets Manager,
      # not hardcoded environment variables. Terraform retrieves them at
      # task launch time and injects them into the container.
      # For this learning project, no secrets are injected here.
      # To add an OpenAI key in production, use aws_secretsmanager_secret
      # and reference it here as: { name = "OPENAI_API_KEY", valueFrom = "<arn>" }
      secrets = []

      logConfiguration = {
        logDriver = "awslogs"
        # awslogs: streams container stdout/stderr to CloudWatch.
        # The ECS agent (using the execution role) handles this automatically.
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
          # Log streams will be named: api/api/<task-id>
        }
      }

      # Health check at the container level (separate from ALB health check).
      # ECS uses this to decide if the container is healthy.
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60  # Grace period after container start (app startup time)
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-api-task"
  }
}

# ── UI Task Definition ────────────────────────────────────────
resource "aws_ecs_task_definition" "ui" {
  family                   = "${var.project_name}-ui"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ui_cpu     # 256 = 0.25 vCPU
  memory                   = var.ui_memory  # 512 = 0.5 GB
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "ui"
      image     = var.ui_image_uri
      essential = true

      portMappings = [
        {
          containerPort = 8501  # Streamlit's default port
          hostPort      = 8501
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "API_URL"
          # The UI needs to know where the API is. Since both services are
          # behind the same ALB, the UI calls the ALB's URL/api.
          # This creates a round-trip: Browser → ALB → UI → ALB → API.
          # In production, you'd use service discovery (Cloud Map) to call
          # the API directly by internal DNS, avoiding the extra ALB hop.
          value = "http://${aws_lb.main.dns_name}/api"
        },
        {
          name  = "STREAMLIT_SERVER_PORT"
          value = "8501"
        },
        {
          name  = "STREAMLIT_SERVER_ADDRESS"
          value = "0.0.0.0"
          # Must bind to all interfaces, not just localhost.
        },
        {
          name  = "STREAMLIT_SERVER_HEADLESS"
          value = "true"
          # Headless mode: disables the browser auto-open and telemetry
          # prompts. Essential for running Streamlit in a container.
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ui.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ui"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8501/_stcore/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 90  # Streamlit takes longer to start than FastAPI
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-ui-task"
  }
}

# ════════════════════════════════════════════════════════════
# ECS SERVICES
# ════════════════════════════════════════════════════════════
# An ECS Service ensures a specified number of task instances
# are always running. If a task crashes, the service scheduler
# starts a replacement automatically.
#
# Service vs Task:
#   Task:    One-time execution (like a batch job or DB migration)
#   Service: Long-running, self-healing (like a web server)
#
# The service also handles rolling deployments — when you update
# the task definition, it starts new tasks, waits for health checks,
# then stops old tasks. Zero downtime.

# ── API ECS Service ───────────────────────────────────────────
resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-api-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count  # How many task copies to run

  launch_type = "FARGATE"
  # Fargate: no EC2 instances to manage. AWS provisions compute on demand.

  # DEPLOYMENT CONFIGURATION
  # Controls how rolling updates work.
  deployment_minimum_healthy_percent = 50
  # During deployment, keep at least 50% of tasks running.
  # With desired_count=1, this means: start new task BEFORE stopping old one.

  deployment_maximum_percent = 200
  # Can temporarily run up to 200% of desired_count during deployment.
  # With desired_count=1, can run 2 tasks simultaneously during rollout.

  # NETWORK CONFIGURATION
  # Required for Fargate with awsvpc networking.
  # Places tasks in the same VPC/subnets as the ALB.
  network_configuration {
    subnets = [
      aws_subnet.public_az1.id,
      aws_subnet.public_az2.id
    ]
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
    # assign_public_ip: true is needed so tasks in public subnets can reach
    # the internet (ECR, CloudWatch, external APIs).
    # In production: use private subnets + NAT Gateway instead (more secure,
    # but NAT Gateway costs ~$32/month — overkill for learning).
  }

  # LOAD BALANCER INTEGRATION
  # Registers each task's IP with the ALB target group.
  # ECS manages this automatically as tasks start/stop.
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"    # Must match the name in task_definition
    container_port   = 8000
  }

  # Wait for the ALB target group to be attached to the listener
  # before creating the service. Without this, ECS might start tasks
  # before the ALB is ready to route to them.
  depends_on = [
    aws_lb_listener_rule.api,
    aws_iam_role_policy_attachment.ecs_task_execution
  ]

  tags = {
    Name = "${var.project_name}-api-service"
  }
}

# ── UI ECS Service ────────────────────────────────────────────
resource "aws_ecs_service" "ui" {
  name            = "${var.project_name}-ui-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ui.arn
  desired_count   = var.ui_desired_count

  launch_type = "FARGATE"

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  network_configuration {
    subnets = [
      aws_subnet.public_az1.id,
      aws_subnet.public_az2.id
    ]
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ui.arn
    container_name   = "ui"
    container_port   = 8501
  }

  depends_on = [
    aws_lb_listener.http,
    aws_iam_role_policy_attachment.ecs_task_execution
  ]

  tags = {
    Name = "${var.project_name}-ui-service"
  }
}
