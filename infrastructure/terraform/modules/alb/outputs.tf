output "controller_iam_role_arn" {
  description = "IAM role ARN for a future AWS Load Balancer Controller Pod Identity association."
  value       = var.enabled ? aws_iam_role.controller[0].arn : null
}

output "controller_iam_policy_arn" {
  description = "Pinned AWS Load Balancer Controller IAM policy ARN."
  value       = var.enabled ? aws_iam_policy.controller[0].arn : null
}

output "controller_pod_identity_association_arn" {
  description = "EKS Pod Identity association ARN for kube-system/aws-load-balancer-controller."
  value       = var.enabled ? aws_eks_pod_identity_association.controller[0].association_arn : null
}
