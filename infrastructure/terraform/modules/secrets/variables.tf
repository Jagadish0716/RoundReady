variable "name_prefix" {
  description = "Environment-qualified prefix ensuring secrets never cross environments."
  type        = string
}

variable "secrets" {
  description = "Secret containers to create without values or versions."
  type = map(object({
    description = string
    owner       = string
  }))
}

variable "recovery_window_days" {
  description = "Secrets Manager deletion recovery window; zero is for disposable environments only."
  type        = number

  validation {
    condition     = var.recovery_window_days == 0 || (var.recovery_window_days >= 7 && var.recovery_window_days <= 30)
    error_message = "recovery_window_days must be zero or between 7 and 30."
  }
}

variable "common_tags" {
  description = "Non-sensitive tags for secret containers."
  type        = map(string)
  default     = {}
}
