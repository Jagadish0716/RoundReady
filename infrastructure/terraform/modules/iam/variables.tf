variable "name_prefix" {
  description = "Environment-qualified IAM resource prefix."
  type        = string
}

variable "cluster_name" {
  description = "EKS cluster receiving Pod Identity associations."
  type        = string
}

variable "cluster_arn" {
  description = "Exact EKS cluster ARN permitted by role trust conditions."
  type        = string
}

variable "namespace" {
  description = "Application Kubernetes namespace used in Pod Identity trust and associations."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", var.namespace))
    error_message = "namespace must be a valid Kubernetes namespace name."
  }
}

variable "service_secret_arns" {
  description = "Exact readable secret ARNs keyed by service-account name."
  type        = map(list(string))

  validation {
    condition     = alltrue([for arns in values(var.service_secret_arns) : length(arns) > 0])
    error_message = "Every workload identity must have at least one explicitly assigned secret ARN."
  }
}

variable "create_pod_identity_associations" {
  description = "Create AWS-side associations; Kubernetes ServiceAccounts may be created later."
  type        = bool
  default     = true
}

variable "common_tags" {
  description = "Non-sensitive tags for workload IAM resources."
  type        = map(string)
  default     = {}
}
