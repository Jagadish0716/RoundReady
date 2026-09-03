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
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
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
