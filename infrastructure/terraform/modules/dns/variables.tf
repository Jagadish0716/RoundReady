variable "enabled" {
  description = "Create public certificate and Route 53 DNS validation records."
  type        = bool
}

variable "name_prefix" {
  description = "Environment-qualified resource name prefix."
  type        = string
}

variable "hosted_zone_id" {
  description = "Optional ID of an existing public Route 53 hosted zone."
  type        = string
  default     = null
  nullable    = true
}

variable "hosted_zone_name" {
  description = "Optional name of an existing public Route 53 hosted zone to look up."
  type        = string
  default     = null
  nullable    = true
}

variable "frontend_domain" {
  description = "Public frontend hostname covered by the ACM certificate."
  type        = string
  default     = null
  nullable    = true
}

variable "api_domain" {
  description = "Public API gateway hostname covered by the ACM certificate."
  type        = string
  default     = null
  nullable    = true
}

variable "alb_dns_name" {
  description = "Controller-created public ALB DNS name; null before Ingress reconciliation."
  type        = string
  default     = null
  nullable    = true
}

variable "alb_zone_id" {
  description = "Canonical hosted-zone ID for the controller-created ALB."
  type        = string
  default     = null
  nullable    = true
}

variable "common_tags" {
  description = "Non-sensitive tags for ACM resources."
  type        = map(string)
  default     = {}
}
