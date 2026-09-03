output "hosted_zone_id" {
  description = "Existing public Route 53 hosted zone ID used for validation."
  value       = local.hosted_zone_id
}

output "certificate_arn" {
  description = "Validated regional ACM certificate ARN for the future ALB."
  value       = var.enabled ? aws_acm_certificate_validation.this[0].certificate_arn : null
}

output "frontend_hostname" {
  description = "Configured public frontend hostname."
  value       = var.enabled ? var.frontend_domain : null
}

output "api_hostname" {
  description = "Configured public API gateway hostname."
  value       = var.enabled ? var.api_domain : null
}
