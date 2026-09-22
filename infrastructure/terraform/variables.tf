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
  description = "Deployment environment with independent Terraform state."
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be dev, staging, or production."
  }
}

variable "aws_region" {
  description = "AWS region for this environment."
  type        = string
  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "aws_region must be a valid AWS region name."
  }
}

variable "common_tags" {
  description = "Additional non-sensitive tags applied to managed resources."
  type        = map(string)
  default     = {}
}

variable "vpc_cidr" {
  description = "IPv4 CIDR for the environment VPC."
  type        = string
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0)) && can(cidrsubnet(var.vpc_cidr, 5, 17))
    error_message = "vpc_cidr must be a valid IPv4 block large enough for six subnets."
  }
}

variable "az_count" {
  description = "Number of Availability Zones used by the VPC."
  type        = number
  default     = 2
  validation {
    condition     = var.az_count == 2
    error_message = "This RoundReady network layout is designed for exactly two AZs."
  }
}

variable "nat_gateway_mode" {
  description = "NAT topology; dev uses one shared NAT Gateway."
  type        = string
  default     = "single"
  validation {
    condition     = contains(["one_per_az", "single"], var.nat_gateway_mode)
    error_message = "nat_gateway_mode must be one_per_az or single."
  }
}

variable "enable_flow_logs" {
  description = "Whether VPC Flow Logs are enabled."
  type        = bool
  default     = false
}

variable "k3s_instance_type" {
  description = "ARM64 EC2 type for both private K3s nodes."
  type        = string
  default     = "t4g.small"
}

variable "k3s_root_volume_size" {
  description = "Encrypted gp3 root volume size in GiB for each K3s node."
  type        = number
  default     = 30
}

variable "k3s_ami_ssm_parameter" {
  description = "AWS public SSM parameter resolving the current Ubuntu 24.04 ARM64 AMI."
  type        = string
  default     = "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id"
}

variable "ec2_key_name" {
  description = "Name of an existing EC2 key pair attached to both K3s nodes."
  type        = string
}

variable "rds_postgres_version" {
  description = "Amazon RDS PostgreSQL major version."
  type        = string
  default     = "16"
}

variable "rds_instance_class" {
  description = "Environment-appropriate RDS instance class."
  type        = string
}

variable "rds_allocated_storage" {
  description = "Initial RDS gp3 storage in GiB."
  type        = number
}

variable "rds_max_allocated_storage" {
  description = "Maximum RDS storage autoscaling allocation in GiB."
  type        = number
}

variable "rds_multi_az" {
  description = "Whether RDS uses Multi-AZ."
  type        = bool
}

variable "rds_backup_retention_days" {
  description = "RDS automated backup retention in days."
  type        = number
}

variable "rds_deletion_protection" {
  description = "RDS deletion protection; disabled for disposable DEV."
  type        = bool
}

variable "rds_skip_final_snapshot" {
  description = "Skip final snapshot for disposable DEV."
  type        = bool
}

variable "rds_apply_immediately" {
  description = "Apply RDS changes immediately."
  type        = bool
  default     = false
}

variable "rds_performance_insights_enabled" {
  description = "Enable RDS Performance Insights."
  type        = bool
  default     = false
}

variable "rds_monitoring_interval" {
  description = "Enhanced Monitoring interval in seconds; zero disables it."
  type        = number
  default     = 0
}

variable "rds_cloudwatch_log_exports" {
  description = "RDS PostgreSQL log types exported to CloudWatch."
  type        = list(string)
  default     = []
}

variable "managed_secret_recovery_window_days" {
  description = "Secret recovery days, or zero for immediate DEV deletion."
  type        = number
  default     = 0
  validation {
    condition     = var.managed_secret_recovery_window_days == 0 || (var.managed_secret_recovery_window_days >= 7 && var.managed_secret_recovery_window_days <= 30)
    error_message = "managed_secret_recovery_window_days must be zero or between 7 and 30."
  }
}

variable "redis_engine" {
  description = "Redis-compatible ElastiCache engine."
  type        = string
  default     = "valkey"
}

variable "redis_engine_version" {
  description = "Pinned Valkey engine version."
  type        = string
  default     = "8.0"
}

variable "redis_node_type" {
  description = "Environment-appropriate ElastiCache node type."
  type        = string
}

variable "redis_replica_count" {
  description = "Number of Valkey replicas."
  type        = number
}

variable "redis_multi_az" {
  description = "Whether Valkey uses Multi-AZ failover."
  type        = bool
}

variable "redis_snapshot_retention_days" {
  description = "Valkey snapshot retention in days."
  type        = number
}

variable "redis_apply_immediately" {
  description = "Apply Valkey changes immediately."
  type        = bool
  default     = false
}

variable "rabbitmq_engine_version" {
  description = "Pinned Amazon MQ RabbitMQ engine version."
  type        = string
  default     = "3.13"
}

variable "rabbitmq_instance_type" {
  description = "Environment-appropriate RabbitMQ broker instance type."
  type        = string
}

variable "rabbitmq_deployment_mode" {
  description = "RabbitMQ deployment mode."
  type        = string
}

variable "rabbitmq_general_log_enabled" {
  description = "Enable RabbitMQ general logs in CloudWatch."
  type        = bool
  default     = true
}

variable "rabbitmq_apply_immediately" {
  description = "Apply RabbitMQ changes immediately."
  type        = bool
  default     = false
}

variable "ecr_image_tag_mutability" {
  description = "ECR repository tag mutability mode."
  type        = string
  default     = "IMMUTABLE"
}

variable "ecr_scan_on_push" {
  description = "Enable ECR image scanning on push."
  type        = bool
  default     = true
}

variable "ecr_tagged_image_retention_count" {
  description = "Number of newest tagged ECR images retained per repository."
  type        = number
}

variable "ecr_untagged_retention_days" {
  description = "Days before untagged ECR images expire."
  type        = number
}

variable "ecr_force_delete" {
  description = "Allow deleting non-empty ECR repositories; enabled for DEV teardown."
  type        = bool
  default     = false
}

variable "application_log_retention_days" {
  description = "CloudWatch application log retention in days."
  type        = number
}

variable "aws_native_alarms_enabled" {
  description = "Whether to create optional AWS-native database alarms."
  type        = bool
  default     = false
}

variable "rds_cpu_alarm_threshold_percent" {
  description = "RDS CPU alarm threshold."
  type        = number
  default     = 80
}

variable "rds_free_storage_alarm_bytes" {
  description = "RDS free-storage alarm threshold in bytes."
  type        = number
  default     = 10737418240
}
