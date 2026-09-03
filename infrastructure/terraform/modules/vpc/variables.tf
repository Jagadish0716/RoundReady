variable "name_prefix" {
  description = "Environment-qualified resource name prefix."
  type        = string
}

variable "vpc_cidr" {
  description = "IPv4 CIDR for the VPC."
  type        = string
}

variable "az_count" {
  description = "Number of available AZs to use."
  type        = number
}

variable "nat_gateway_mode" {
  description = "one_per_az for resilient NAT or single for cost-sensitive environments."
  type        = string
}

variable "enable_flow_logs" {
  description = "Whether to create CloudWatch VPC Flow Logs."
  type        = bool
}

variable "common_tags" {
  description = "Non-sensitive tags for VPC resources."
  type        = map(string)
  default     = {}
}
