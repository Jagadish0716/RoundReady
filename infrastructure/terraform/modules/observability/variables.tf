variable "name_prefix" {
  description = "Environment-qualified observability resource prefix."
  type        = string
}

variable "environment" {
  description = "Environment used in non-sensitive log-group naming."
  type        = string
}

variable "application_log_retention_days" {
  description = "CloudWatch application log retention in days."
  type        = number

  validation {
    condition = contains(
      [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
      var.application_log_retention_days,
    )
    error_message = "application_log_retention_days must be a CloudWatch-supported retention period."
  }
}

variable "aws_native_alarms_enabled" {
  description = "Create the small AWS-native RDS alarm baseline and unsubscribed SNS topic."
  type        = bool
}

variable "rds_instance_identifier" {
  description = "RDS instance dimension for reliable AWS/RDS metrics."
  type        = string
}

variable "rds_cpu_alarm_threshold_percent" {
  description = "Initial RDS CPU alarm threshold percentage."
  type        = number
  default     = 80

  validation {
    condition     = var.rds_cpu_alarm_threshold_percent > 0 && var.rds_cpu_alarm_threshold_percent <= 100
    error_message = "rds_cpu_alarm_threshold_percent must be greater than zero and at most 100."
  }
}

variable "rds_free_storage_alarm_bytes" {
  description = "Initial RDS free-storage alarm threshold in bytes."
  type        = number
  default     = 10737418240

  validation {
    condition     = var.rds_free_storage_alarm_bytes > 0
    error_message = "rds_free_storage_alarm_bytes must be greater than zero."
  }
}

variable "common_tags" {
  description = "Non-sensitive observability tags."
  type        = map(string)
  default     = {}
}
