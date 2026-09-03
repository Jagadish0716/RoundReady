variable "enabled" {
  description = "Create AWS Load Balancer Controller IAM prerequisites."
  type        = bool
}

variable "name_prefix" {
  description = "Environment-qualified resource name prefix."
  type        = string
}

variable "cluster_name" {
  description = "EKS cluster name for the controller Pod Identity association."
  type        = string

  validation {
    condition     = length(trimspace(var.cluster_name)) > 0
    error_message = "cluster_name must not be empty."
  }
}

variable "controller_version" {
  description = "AWS Load Balancer Controller version matching the committed IAM policy."
  type        = string
  default     = "v2.14.1"

  validation {
    condition     = var.controller_version == "v2.14.1"
    error_message = "controller_version must remain v2.14.1 until the committed IAM policy is reviewed and updated."
  }
}

variable "common_tags" {
  description = "Non-sensitive tags for controller IAM resources."
  type        = map(string)
  default     = {}
}
