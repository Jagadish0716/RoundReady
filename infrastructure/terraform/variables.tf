variable "project_name" {
  description = "Project name used in resource naming and tags."
  type        = string
  default     = "roundready"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "project_name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Deployment environment with an independent Terraform state."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be dev, staging, or production."
  }
}

variable "aws_region" {
  description = "AWS region for this environment. Production must set this explicitly."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "aws_region must be a valid AWS region name."
  }
}

variable "common_tags" {
  description = "Additional non-sensitive tags applied to future managed resources."
  type        = map(string)
  default     = {}
}

variable "vpc_cidr" {
  description = "Non-overlapping IPv4 CIDR for this environment VPC."
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0)) && can(cidrsubnet(var.vpc_cidr, 5, 17))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block large enough for the public, application, and data subnet tiers."
  }
}

variable "az_count" {
  description = "Number of discovered Availability Zones used by the VPC."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 6 && floor(var.az_count) == var.az_count
    error_message = "az_count must be an integer between 2 and 6."
  }
}

variable "nat_gateway_mode" {
  description = "NAT Gateway topology: one_per_az for resilience or single for lower cost."
  type        = string
  default     = "one_per_az"

  validation {
    condition     = contains(["one_per_az", "single"], var.nat_gateway_mode)
    error_message = "nat_gateway_mode must be one_per_az or single."
  }
}

variable "enable_flow_logs" {
  description = "Create VPC Flow Logs and their minimal CloudWatch destination."
  type        = bool
  default     = false
}

variable "kubernetes_version" {
  description = "Pinned EKS Kubernetes minor version."
  type        = string
  default     = "1.33"
}

variable "node_instance_types" {
  description = "On-demand EKS managed node instance types."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_min_size" {
  description = "Minimum nodes in the general application managed node group."
  type        = number
  default     = 2
}

variable "node_desired_size" {
  description = "Desired nodes in the general application managed node group."
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum nodes in the general application managed node group."
  type        = number
  default     = 4
}

variable "node_disk_size" {
  description = "Managed node root EBS volume size in GiB."
  type        = number
  default     = 50
}

variable "enable_public_eks_endpoint" {
  description = "Allow public EKS API endpoint access in addition to private access."
  type        = bool
  default     = false
}

variable "eks_public_access_cidrs" {
  description = "Explicit administrator CIDRs allowed when public EKS access is enabled."
  type        = list(string)
  default     = []
}

variable "enable_eks_control_plane_logs" {
  description = "Enable EKS API, audit, authenticator, controller, and scheduler logs."
  type        = bool
  default     = false
}

variable "eks_admin_principal_arns" {
  description = "Optional IAM principal ARNs receiving future EKS access entries."
  type        = list(string)
  default     = []
}

variable "rds_postgres_version" {
  description = "Pinned Amazon RDS PostgreSQL major version."
  type        = string
  default     = "16"
}

variable "rds_instance_class" {
  description = "Environment-appropriate Amazon RDS instance class."
  type        = string
}

variable "rds_allocated_storage" {
  description = "Initial RDS gp3 storage allocation in GiB."
  type        = number
}

variable "rds_max_allocated_storage" {
  description = "Maximum RDS storage autoscaling allocation in GiB."
  type        = number
}

variable "rds_multi_az" {
  description = "Enable a synchronous Multi-AZ standby."
  type        = bool
}

variable "rds_backup_retention_days" {
  description = "RDS automated backup retention in days."
  type        = number
}

variable "rds_deletion_protection" {
  description = "Protect the RDS instance from deletion."
  type        = bool
}

variable "rds_skip_final_snapshot" {
  description = "Skip the final RDS snapshot on destroy; prohibited in production."
  type        = bool
}

variable "rds_apply_immediately" {
  description = "Apply RDS modifications immediately rather than in its maintenance window."
  type        = bool
  default     = false
}

variable "rds_performance_insights_enabled" {
  description = "Enable RDS Performance Insights."
  type        = bool
  default     = false
}

variable "rds_monitoring_interval" {
  description = "RDS Enhanced Monitoring interval in seconds; zero disables it."
  type        = number
  default     = 0
}

variable "rds_cloudwatch_log_exports" {
  description = "RDS PostgreSQL log streams exported to CloudWatch Logs."
  type        = list(string)
  default     = []
}

variable "managed_secret_recovery_window_days" {
  description = "Recovery window for generated managed-service credential secrets."
  type        = number
  default     = 7

  validation {
    condition     = var.managed_secret_recovery_window_days == 0 || (var.managed_secret_recovery_window_days >= 7 && var.managed_secret_recovery_window_days <= 30)
    error_message = "managed_secret_recovery_window_days must be zero or between 7 and 30."
  }
}

variable "redis_engine" {
  description = "ElastiCache Redis-compatible engine."
  type        = string
  default     = "valkey"
}

variable "redis_engine_version" {
  description = "Pinned ElastiCache engine version."
  type        = string
  default     = "8.0"
}

variable "redis_node_type" {
  description = "Environment-appropriate ElastiCache node type."
  type        = string
}

variable "redis_replica_count" {
  description = "Number of Redis replicas."
  type        = number
}

variable "redis_multi_az" {
  description = "Enable Redis Multi-AZ failover."
  type        = bool
}

variable "redis_snapshot_retention_days" {
  description = "ElastiCache automatic snapshot retention in days."
  type        = number
}

variable "redis_apply_immediately" {
  description = "Apply ElastiCache modifications immediately."
  type        = bool
  default     = false
}

variable "rabbitmq_engine_version" {
  description = "Pinned Amazon MQ RabbitMQ engine version."
  type        = string
  default     = "3.13"
}

variable "rabbitmq_instance_type" {
  description = "Environment-appropriate Amazon MQ broker instance type."
  type        = string
}

variable "rabbitmq_deployment_mode" {
  description = "Amazon MQ RabbitMQ deployment mode."
  type        = string
}

variable "rabbitmq_general_log_enabled" {
  description = "Enable supported RabbitMQ general logs in CloudWatch."
  type        = bool
  default     = true
}

variable "rabbitmq_apply_immediately" {
  description = "Apply Amazon MQ modifications immediately."
  type        = bool
  default     = false
}

variable "load_balancer_controller_enabled" {
  description = "Create IAM prerequisites for the future AWS Load Balancer Controller."
  type        = bool
  default     = false
}

variable "load_balancer_controller_version" {
  description = "Controller release matching the reviewed IAM policy."
  type        = string
  default     = "v2.14.1"
}

variable "public_ingress_enabled" {
  description = "Create Route 53 validation records and a regional ACM certificate."
  type        = bool
  default     = false
}

variable "hosted_zone_id" {
  description = "Optional ID of an existing public Route 53 hosted zone."
  type        = string
  default     = null
  nullable    = true
}

variable "hosted_zone_name" {
  description = "Optional name of an existing public Route 53 hosted zone."
  type        = string
  default     = null
  nullable    = true
}

variable "frontend_domain" {
  description = "Explicit public frontend hostname when ingress is enabled."
  type        = string
  default     = null
  nullable    = true
}

variable "api_domain" {
  description = "Explicit public API gateway hostname when ingress is enabled."
  type        = string
  default     = null
  nullable    = true
}

variable "public_alb_dns_name" {
  description = "Controller-created public ALB DNS name; null until Kubernetes Ingress exists."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.public_alb_dns_name == null || can(regex("^[A-Za-z0-9.-]+\\.elb\\.[a-z0-9-]+\\.amazonaws\\.com$", var.public_alb_dns_name))
    error_message = "public_alb_dns_name must be a valid AWS ALB DNS name or null."
  }
}

variable "public_alb_zone_id" {
  description = "Canonical hosted-zone ID of the controller-created public ALB; null until it exists."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.public_alb_zone_id == null || can(regex("^Z[A-Z0-9]+$", var.public_alb_zone_id))
    error_message = "public_alb_zone_id must be a valid AWS hosted-zone ID or null."
  }
}

variable "application_namespace" {
  description = "Kubernetes namespace reserved for RoundReady application workloads."
  type        = string
  default     = "roundready"
}

variable "create_pod_identity_associations" {
  description = "Create AWS-side Pod Identity associations for future workload ServiceAccounts."
  type        = bool
  default     = true
}

variable "ecr_image_tag_mutability" {
  description = "ECR image tag mutability mode."
  type        = string
  default     = "IMMUTABLE"
}

variable "ecr_scan_on_push" {
  description = "Enable basic ECR vulnerability scanning on image push."
  type        = bool
  default     = true
}

variable "ecr_tagged_image_retention_count" {
  description = "Number of recent tagged images retained per repository."
  type        = number
}

variable "ecr_untagged_retention_days" {
  description = "Days to retain untagged ECR images."
  type        = number
}

variable "ecr_force_delete" {
  description = "Allow deletion of non-empty ECR repositories; prohibited in production."
  type        = bool
  default     = false
}

variable "application_log_retention_days" {
  description = "CloudWatch retention for future application workload logs."
  type        = number
}

variable "aws_native_alarms_enabled" {
  description = "Create the initial reliable AWS-native RDS alarms."
  type        = bool
  default     = false
}

variable "rds_cpu_alarm_threshold_percent" {
  description = "Initial RDS CPU utilization alarm threshold."
  type        = number
  default     = 80
}

variable "rds_free_storage_alarm_bytes" {
  description = "Initial RDS free-storage alarm threshold in bytes."
  type        = number
  default     = 10737418240
}
