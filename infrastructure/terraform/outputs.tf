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

output "rds_endpoint" {
  description = "Private RDS PostgreSQL endpoint including port."
  value       = module.rds.endpoint
}

output "rds_port" {
  description = "RDS PostgreSQL listener port."
  value       = module.rds.port
}

output "rds_instance_identifier" {
  description = "RDS PostgreSQL instance identifier."
  value       = module.rds.instance_identifier
}

output "rds_security_group_id" {
  description = "RDS PostgreSQL security group ID."
  value       = module.rds.security_group_id
}

output "rds_subnet_group_name" {
  description = "Private RDS subnet group name."
  value       = module.rds.subnet_group_name
}

output "rds_master_secret_arn" {
  description = "ARN of the AWS-managed RDS master credential secret."
  value       = module.rds.master_secret_arn
}

output "redis_primary_endpoint" {
  description = "Private TLS Redis primary endpoint address."
  value       = module.redis.primary_endpoint
}

output "redis_reader_endpoint" {
  description = "Private TLS Redis reader endpoint address."
  value       = module.redis.reader_endpoint
}

output "redis_port" {
  description = "Redis protocol port."
  value       = module.redis.port
}

output "redis_replication_group_id" {
  description = "ElastiCache replication group ID."
  value       = module.redis.replication_group_id
}

output "redis_security_group_id" {
  description = "ElastiCache security group ID."
  value       = module.redis.security_group_id
}

output "redis_credentials_secret_arn" {
  description = "ARN of the Redis credential secret."
  value       = module.redis.credentials_secret_arn
}

output "rabbitmq_broker_id" {
  description = "Amazon MQ RabbitMQ broker ID."
  value       = module.rabbitmq.broker_id
}

output "rabbitmq_broker_arn" {
  description = "Amazon MQ RabbitMQ broker ARN."
  value       = module.rabbitmq.broker_arn
}

output "rabbitmq_amqps_endpoints" {
  description = "Private RabbitMQ AMQPS endpoints without credentials."
  value       = module.rabbitmq.amqps_endpoints
}

output "rabbitmq_security_group_id" {
  description = "Amazon MQ RabbitMQ security group ID."
  value       = module.rabbitmq.security_group_id
}

output "rabbitmq_credentials_secret_arn" {
  description = "ARN of the RabbitMQ credential secret."
  value       = module.rabbitmq.credentials_secret_arn
}

output "public_hosted_zone_id" {
  description = "Existing public Route 53 hosted zone ID used for certificate validation."
  value       = module.dns.hosted_zone_id
}

output "public_certificate_arn" {
  description = "Validated ACM certificate ARN for the future ingress-managed ALB."
  value       = module.dns.certificate_arn
}

output "frontend_hostname" {
  description = "Configured public frontend hostname."
  value       = module.dns.frontend_hostname
}

output "api_hostname" {
  description = "Configured public API gateway hostname."
  value       = module.dns.api_hostname
}

output "load_balancer_controller_iam_role_arn" {
  description = "IAM role for a future AWS Load Balancer Controller Pod Identity association."
  value       = module.alb.controller_iam_role_arn
}

output "load_balancer_controller_pod_identity_association_arn" {
  description = "Pod Identity association for kube-system/aws-load-balancer-controller."
  value       = module.alb.controller_pod_identity_association_arn
}

output "application_secret_arns" {
  description = "Environment-specific application secret-container ARNs; no values are exposed."
  value       = module.secrets.secret_arns
}

output "workload_iam_role_arns" {
  description = "Service-specific EKS Pod Identity IAM role ARNs."
  value       = module.iam.workload_role_arns
}

output "workload_service_accounts" {
  description = "Intended application ServiceAccount names keyed by service."
  value       = module.iam.service_accounts
}

output "application_namespace" {
  description = "Application namespace used by EKS Pod Identity associations."
  value       = module.iam.namespace
}

output "pod_identity_association_arns" {
  description = "AWS-side service Pod Identity association ARNs."
  value       = module.iam.pod_identity_association_arns
}

output "ecr_repository_names" {
  description = "Private ECR repository names keyed by deployable component."
  value       = module.ecr.repository_names
}

output "ecr_repository_arns" {
  description = "Private ECR repository ARNs keyed by deployable component."
  value       = module.ecr.repository_arns
}

output "ecr_repository_urls" {
  description = "Private ECR repository URLs keyed by deployable component."
  value       = module.ecr.repository_urls
}

output "application_log_group_name" {
  description = "Shared CloudWatch application log-group name."
  value       = module.observability.application_log_group_name
}

output "application_log_group_arn" {
  description = "Shared CloudWatch application log-group ARN."
  value       = module.observability.application_log_group_arn
}

output "infrastructure_alarm_topic_arn" {
  description = "Optional unsubscribed SNS topic ARN for infrastructure alarms."
  value       = module.observability.alarm_topic_arn
}

output "aws_native_alarm_arns" {
  description = "Initial reliable AWS-native alarm ARNs."
  value       = module.observability.alarm_arns
}
