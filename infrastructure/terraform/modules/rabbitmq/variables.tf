variable "name_prefix" {
  description = "Environment-qualified resource name prefix."
  type        = string
}

variable "vpc_id" {
  description = "VPC containing the private broker."
  type        = string
}

variable "private_data_subnet_ids" {
  description = "Private data subnets used by Amazon MQ."
  type        = list(string)

  validation {
    condition     = length(var.private_data_subnet_ids) >= 1
    error_message = "private_data_subnet_ids must contain at least one subnet."
  }
}

variable "application_security_group_id" {
  description = "EKS application security group allowed to connect over AMQPS."
  type        = string
}

variable "production_mode" {
  description = "Enforce the production broker availability baseline."
  type        = bool
}

variable "engine_version" {
  description = "Pinned Amazon MQ RabbitMQ engine version."
  type        = string
  default     = "3.13"
}

variable "instance_type" {
  description = "Amazon MQ broker instance type."
  type        = string

  validation {
    condition     = startswith(var.instance_type, "mq.")
    error_message = "instance_type must be a valid Amazon MQ type beginning with mq."
  }
}

variable "deployment_mode" {
  description = "RabbitMQ deployment mode."
  type        = string

  validation {
    condition     = contains(["SINGLE_INSTANCE", "CLUSTER_MULTI_AZ"], var.deployment_mode)
    error_message = "deployment_mode must be SINGLE_INSTANCE or CLUSTER_MULTI_AZ."
  }
}

variable "username" {
  description = "Non-secret initial RabbitMQ administrator username."
  type        = string
  default     = "roundready"
}

variable "general_log_enabled" {
  description = "Enable supported Amazon MQ general logs in CloudWatch."
  type        = bool
  default     = true
}

variable "maintenance_day" {
  description = "UTC maintenance day."
  type        = string
  default     = "SUNDAY"
}

variable "maintenance_time" {
  description = "UTC maintenance time in HH:MM format."
  type        = string
  default     = "20:00"
}

variable "auto_minor_version_upgrade" {
  description = "Allow Amazon MQ minor engine updates during maintenance."
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Apply broker modifications immediately rather than during maintenance."
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
  description = "Non-sensitive tags for RabbitMQ resources."
  type        = map(string)
  default     = {}
}
