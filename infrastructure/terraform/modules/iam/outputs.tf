output "workload_role_arns" {
  description = "Service-specific Pod Identity IAM role ARNs."
  value       = { for service, role in aws_iam_role.service : service => role.arn }
}

output "service_accounts" {
  description = "Intended Kubernetes ServiceAccount names keyed by service."
  value       = local.service_accounts
}

output "namespace" {
  description = "Configured application Kubernetes namespace."
  value       = var.namespace
}

output "pod_identity_association_arns" {
  description = "AWS-side EKS Pod Identity association ARNs."
  value = {
    for service, association in aws_eks_pod_identity_association.service :
    service => association.association_arn
  }
}
