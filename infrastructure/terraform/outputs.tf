output "name_prefix" {
  description = "Canonical environment resource prefix."
  value       = local.name_prefix
}

output "aws_account_id" {
  description = "AWS account selected by the configured credentials."
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "Configured AWS region."
  value       = var.aws_region
}

output "vpc_id" {
  description = "Environment VPC ID."
  value       = module.network.vpc_id
}

output "vpc_cidr" {
  description = "Environment VPC CIDR."
  value       = module.network.vpc_cidr
}

output "public_subnet_ids" {
  description = "Public subnet IDs used by the ALB."
  value       = module.network.public_subnet_ids
}

output "private_app_subnet_ids" {
  description = "Private application subnet IDs used by K3s."
  value       = module.network.private_app_subnet_ids
}

output "private_data_subnet_ids" {
  description = "Private data subnet IDs used by managed databases and brokers."
  value       = module.network.private_data_subnet_ids
}

output "k3s_server_instance_id" {
  description = "K3s server/control-plane instance ID."
  value       = module.k3s.server_instance_id
}

output "k3s_worker_instance_id" {
  description = "K3s worker instance ID."
  value       = module.k3s.worker_instance_id
}

output "k3s_server_private_ip" {
  description = "K3s server private IP."
  value       = module.k3s.server_private_ip
}

output "k3s_worker_private_ip" {
  description = "K3s worker private IP."
  value       = module.k3s.worker_private_ip
}

output "k3s_node_security_group_id" {
  description = "Security group shared by the private K3s nodes."
  value       = module.k3s.security_group_id
}

output "k3s_join_token_parameter_name" {
  description = "Terraform-owned SSM SecureString parameter path; no token value is exposed."
  value       = module.k3s.join_token_parameter_name
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
  description = "RDS security group ID."
  value       = module.rds.security_group_id
}

output "rds_master_secret_arn" {
  description = "ARN of the AWS-managed RDS master credential secret."
  value       = module.rds.master_secret_arn
}

output "valkey_primary_endpoint" {
  description = "Private TLS Valkey primary endpoint."
  value       = module.redis.primary_endpoint
}

output "valkey_reader_endpoint" {
  description = "Private TLS Valkey reader endpoint."
  value       = module.redis.reader_endpoint
}

output "valkey_security_group_id" {
  description = "Valkey security group ID."
  value       = module.redis.security_group_id
}

output "valkey_credentials_secret_arn" {
  description = "ARN of the Valkey credentials secret; no secret value is exposed."
  value       = module.redis.credentials_secret_arn
}

output "rabbitmq_broker_id" {
  description = "Amazon MQ RabbitMQ broker ID."
  value       = module.rabbitmq.broker_id
}

output "rabbitmq_amqps_endpoints" {
  description = "Private RabbitMQ AMQPS endpoints without credentials."
  value       = module.rabbitmq.amqps_endpoints
}

output "rabbitmq_security_group_id" {
  description = "RabbitMQ security group ID."
  value       = module.rabbitmq.security_group_id
}

output "rabbitmq_credentials_secret_arn" {
  description = "ARN of the RabbitMQ credentials secret; no secret value is exposed."
  value       = module.rabbitmq.credentials_secret_arn
}

output "application_secret_arns" {
  description = "Application secret-container ARNs; no secret values are exposed."
  value       = module.secrets.secret_arns
}

output "application_log_group_name" {
  description = "CloudWatch application log group name."
  value       = module.observability.application_log_group_name
}

output "application_log_group_arn" {
  description = "CloudWatch application log group ARN."
  value       = module.observability.application_log_group_arn
}

output "ecr_repository_names" {
  description = "RoundReady ECR repository names keyed by component."
  value       = module.ecr.repository_names
}

output "ecr_repository_arns" {
  description = "RoundReady ECR repository ARNs keyed by component."
  value       = module.ecr.repository_arns
}

output "ecr_repository_urls" {
  description = "RoundReady ECR repository URLs keyed by component."
  value       = module.ecr.repository_urls
}

output "alb_dns_name" {
  description = "Public HTTP ALB DNS name for the RoundReady frontend."
  value       = module.k3s_alb.alb_dns_name
}

output "alb_zone_id" {
  description = "Canonical hosted-zone ID for the frontend ALB."
  value       = module.k3s_alb.alb_zone_id
}

output "alb_security_group_id" {
  description = "Dedicated frontend ALB security group ID."
  value       = module.k3s_alb.alb_security_group_id
}

output "alb_target_group_arn" {
  description = "Frontend NodePort target group ARN."
  value       = module.k3s_alb.target_group_arn
}
