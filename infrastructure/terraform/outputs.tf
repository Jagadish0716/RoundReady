output "name_prefix" {
  description = "Canonical prefix for future environment resources."
  value       = local.name_prefix
}

output "aws_account_id" {
  description = "AWS account discovered from the configured provider credentials."
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "Configured AWS region."
  value       = var.aws_region
}

output "vpc_id" {
  description = "Environment VPC ID."
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for the future ALB."
  value       = module.vpc.public_subnet_ids
}

output "private_app_subnet_ids" {
  description = "Private application subnet IDs for future EKS workloads."
  value       = module.vpc.private_app_subnet_ids
}

output "private_data_subnet_ids" {
  description = "Private data subnet IDs for future managed data services."
  value       = module.vpc.private_data_subnet_ids
}

output "vpc_cidr" {
  description = "Environment VPC CIDR."
  value       = module.vpc.vpc_cidr
}

output "eks_cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN."
  value       = module.eks.cluster_arn
}

output "eks_cluster_endpoint" {
  description = "EKS Kubernetes API endpoint."
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_security_group_id" {
  description = "EKS control-plane primary security group ID."
  value       = module.eks.cluster_security_group_id
}

output "eks_oidc_issuer" {
  description = "EKS OIDC issuer URL for future workload identity integration."
  value       = module.eks.oidc_issuer
}