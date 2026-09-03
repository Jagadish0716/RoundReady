variable "name_prefix" {
  description = "Environment-qualified resource name prefix."
  type        = string
}

variable "vpc_id" {
  description = "VPC containing the private RDS instance."
  type        = string
}

variable "private_data_subnet_ids" {
  description = "Private data subnet IDs in at least two Availability Zones."
  type        = list(string)

  validation {
    condition     = length(var.private_data_subnet_ids) >= 2
    error_message = "private_data_subnet_ids must contain at least two subnets."
  }
}

variable "application_security_group_id" {
  description = "Security group attached to EKS application workloads allowed to reach PostgreSQL."
  type        = string
}

variable "production_mode" {
  description = "Enforce the production availability and deletion-safety baseline."
  type        = bool
}

variable "postgres_version" {
  description = "Pinned PostgreSQL major version supported by Amazon RDS."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.postgres_version))
    error_message = "postgres_version must be a pinned major version such as 16."
  }
}

variable "instance_class" {
  description = "Amazon RDS DB instance class."
  type        = string

  validation {
    condition     = startswith(var.instance_class, "db.")
    error_message = "instance_class must be a valid RDS class beginning with db."
  }
}

variable "master_username" {
  description = "Non-secret master username used only for controlled bootstrap operations."
  type        = string
  default     = "roundready_admin"
}

variable "allocated_storage" {
  description = "Initial gp3 storage allocation in GiB."
  type        = number

  validation {
    condition     = var.allocated_storage >= 20 && floor(var.allocated_storage) == var.allocated_storage
    error_message = "allocated_storage must be an integer of at least 20 GiB."
  }
}

variable "max_allocated_storage" {
  description = "Maximum gp3 storage autoscaling allocation in GiB."
  type        = number
}

variable "multi_az" {
  description = "Deploy a synchronous standby in another Availability Zone."
  type        = bool
}

variable "backup_retention_days" {
  description = "Automated backup retention in days."
  type        = number

  validation {
    condition     = var.backup_retention_days >= 0 && var.backup_retention_days <= 35
    error_message = "backup_retention_days must be between 0 and 35."
  }
}

variable "backup_window" {
  description = "Preferred UTC backup window."
  type        = string
  default     = "18:00-19:00"
}

variable "maintenance_window" {
  description = "Preferred UTC weekly maintenance window."
  type        = string
  default     = "sun:19:00-sun:20:00"
}

variable "deletion_protection" {
  description = "Prevent deletion through the RDS API."
  type        = bool
}

variable "skip_final_snapshot" {
  description = "Skip the final snapshot when the instance is destroyed. Must be false in production."
  type        = bool
}

variable "auto_minor_version_upgrade" {
  description = "Allow minor engine updates during the maintenance window."
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Apply modifications immediately instead of during the maintenance window."
  type        = bool
  default     = false
}

variable "performance_insights_enabled" {
  description = "Enable RDS Performance Insights."
  type        = bool
  default     = false
}

variable "performance_insights_retention_days" {
  description = "Performance Insights retention in days."
  type        = number
  default     = 7

  validation {
    condition = contains(
      [7, 31, 62, 93, 124, 155, 186, 217, 248, 279, 310, 341, 372, 403, 434, 465, 496, 527, 558, 589, 620, 651, 682, 713, 731],
      var.performance_insights_retention_days,
    )
    error_message = "performance_insights_retention_days must be an RDS-supported retention period."
  }
}

variable "monitoring_interval" {
  description = "Enhanced Monitoring interval in seconds; zero disables it."
  type        = number
  default     = 0

  validation {
    condition     = contains([0, 1, 5, 10, 15, 30, 60], var.monitoring_interval)
    error_message = "monitoring_interval must be one of 0, 1, 5, 10, 15, 30, or 60 seconds."
  }
}

variable "cloudwatch_log_exports" {
  description = "RDS PostgreSQL log streams exported to CloudWatch Logs."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for log in var.cloudwatch_log_exports : contains(["postgresql", "upgrade"], log)])
    error_message = "cloudwatch_log_exports may contain only postgresql and upgrade."
  }
}

variable "common_tags" {
  description = "Non-sensitive tags for RDS resources."
  type        = map(string)
  default     = {}
}
