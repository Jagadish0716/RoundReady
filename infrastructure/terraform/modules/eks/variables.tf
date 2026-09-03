variable "name_prefix" {
  description = "Environment-qualified resource name prefix."
  type        = string
}

variable "kubernetes_version" {
  description = "Pinned EKS Kubernetes minor version."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+$", var.kubernetes_version))
    error_message = "kubernetes_version must be a pinned Kubernetes minor version such as 1.33."
  }
}

variable "vpc_id" {
  description = "Existing VPC ID from the VPC module."
  type        = string
}

variable "private_app_subnet_ids" {
  description = "Private application subnet IDs for EKS control plane and nodes."
  type        = list(string)
}

variable "node_instance_types" {
  description = "On-demand managed node instance types."
  type        = list(string)

  validation {
    condition     = length(var.node_instance_types) > 0
    error_message = "node_instance_types must contain at least one instance type."
  }
}

variable "node_min_size" {
  description = "Managed node group minimum size."
  type        = number

  validation {
    condition     = var.node_min_size >= 0 && floor(var.node_min_size) == var.node_min_size
    error_message = "node_min_size must be a non-negative integer."
  }
}

variable "node_desired_size" {
  description = "Managed node group desired size."
  type        = number

  validation {
    condition     = var.node_desired_size >= 0 && floor(var.node_desired_size) == var.node_desired_size
    error_message = "node_desired_size must be a non-negative integer."
  }
}

variable "node_max_size" {
  description = "Managed node group maximum size."
  type        = number

  validation {
    condition     = var.node_max_size >= 0 && floor(var.node_max_size) == var.node_max_size
    error_message = "node_max_size must be a non-negative integer."
  }
}

variable "node_disk_size" {
  description = "Managed node root EBS volume size in GiB."
  type        = number

  validation {
    condition     = var.node_disk_size >= 20 && floor(var.node_disk_size) == var.node_disk_size
    error_message = "node_disk_size must be an integer of at least 20 GiB."
  }
}

variable "enable_public_endpoint" {
  description = "Whether the EKS API endpoint is reachable publicly."
  type        = bool
}

variable "public_access_cidrs" {
  description = "Explicit CIDRs allowed to reach the public EKS endpoint."
  type        = list(string)

}

variable "enable_control_plane_logs" {
  description = "Whether to enable all supported EKS control-plane log types."
  type        = bool
}

variable "admin_principal_arns" {
  description = "IAM principal ARNs receiving operator access entries."
  type        = list(string)
  default     = []
}

variable "common_tags" {
  description = "Non-sensitive tags for EKS resources."
  type        = map(string)
  default     = {}
}
