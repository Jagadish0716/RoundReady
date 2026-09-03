variable "name_prefix" {
  description = "Environment-qualified resource name prefix."
  type        = string
}

variable "vpc_id" {
  description = "VPC containing the private cache."
  type        = string
}

variable "private_data_subnet_ids" {
  description = "Private data subnet IDs used by ElastiCache."
  type        = list(string)

  validation {
    condition     = length(var.private_data_subnet_ids) >= 2
    error_message = "private_data_subnet_ids must contain at least two subnets."
  }
}

variable "application_security_group_id" {
  description = "EKS application security group allowed to connect to Redis."
  type        = string
}

variable "production_mode" {
  description = "Enforce the production availability baseline."
  type        = bool
}

variable "engine" {
  description = "ElastiCache Redis-compatible engine."
  type        = string
  default     = "valkey"

  validation {
    condition     = contains(["valkey", "redis"], var.engine)
    error_message = "engine must be valkey or redis."
  }
}

variable "engine_version" {
  description = "Pinned compatible ElastiCache engine version."
  type        = string
}

variable "node_type" {
  description = "ElastiCache node type."
  type        = string

  validation {
    condition     = startswith(var.node_type, "cache.")
    error_message = "node_type must be a valid ElastiCache type beginning with cache."
  }
}

variable "replica_count" {
  description = "Number of read replicas in the single non-sharded node group."
  type        = number

  validation {
    condition     = var.replica_count >= 0 && var.replica_count <= 5 && floor(var.replica_count) == var.replica_count
    error_message = "replica_count must be an integer between 0 and 5."
  }
}

variable "multi_az" {
  description = "Enable ElastiCache Multi-AZ placement and failover."
  type        = bool
}

variable "snapshot_retention_days" {
  description = "Automatic cache snapshot retention in days."
  type        = number

  validation {
    condition     = var.snapshot_retention_days >= 0 && var.snapshot_retention_days <= 35
    error_message = "snapshot_retention_days must be between 0 and 35."
  }
}

variable "snapshot_window" {
  description = "Preferred UTC snapshot window."
  type        = string
  default     = "17:00-18:00"
}

variable "maintenance_window" {
  description = "Preferred UTC weekly maintenance window."
  type        = string
  default     = "sun:18:00-sun:19:00"
}

variable "auto_minor_version_upgrade" {
  description = "Allow compatible minor engine upgrades during maintenance."
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Apply cache modifications immediately rather than during maintenance."
  type        = bool
  default     = false
}

variable "secret_recovery_window_days" {
  description = "Secrets Manager recovery window; zero is suitable only for disposable environments."
  type        = number
  default     = 7

  validation {
    condition     = var.secret_recovery_window_days == 0 || (var.secret_recovery_window_days >= 7 && var.secret_recovery_window_days <= 30)
    error_message = "secret_recovery_window_days must be zero or between 7 and 30."
  }
}

variable "common_tags" {
  description = "Non-sensitive tags for Redis resources."
  type        = map(string)
  default     = {}
}
