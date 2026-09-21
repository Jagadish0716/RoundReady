terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" { use_lockfile = true }
}
variable "aws_region" {
  type = string
}
variable "environment" {
  type = string
}
variable "project_name" {
  type = string
}
variable "state_bucket" {
  type = string
}
variable "state_region" {
  type = string
}
variable "network_state_key" {
  type = string
}
variable "platform_state_key" {
  type = string
}
variable "rds_instance_class" {
  type = string
}
variable "postgres_version" {
  type    = string
  default = "16"
}
variable "rds_allocated_storage" {
  type = number
}
variable "rds_max_allocated_storage" {
  type = number
}
variable "rds_multi_az" {
  type = bool
}
variable "rds_backup_retention_days" {
  type = number
}
variable "rds_deletion_protection" {
  type = bool
}
variable "rds_skip_final_snapshot" {
  type = bool
}
variable "rds_apply_immediately" {
  type = bool
}
variable "redis_node_type" {
  type = string
}
variable "redis_engine" {
  type    = string
  default = "valkey"
}
variable "redis_engine_version" {
  type    = string
  default = "8.0"
}
variable "redis_replica_count" {
  type = number
}
variable "redis_multi_az" {
  type = bool
}
variable "redis_snapshot_retention_days" {
  type = number
}
variable "redis_apply_immediately" {
  type = bool
}
variable "rabbitmq_instance_type" {
  type = string
}
variable "rabbitmq_engine_version" {
  type    = string
  default = "3.13"
}
variable "rabbitmq_deployment_mode" {
  type = string
}
variable "rabbitmq_general_log_enabled" {
  type = bool
}
variable "rabbitmq_apply_immediately" {
  type = bool
}
variable "managed_secret_recovery_window_days" {
  type = number
}
variable "common_tags" {
  type = map(string)
}
data "terraform_remote_state" "network" {
  backend = "s3"
  config = { bucket = var.state_bucket, key = var.network_state_key, region = var.state_region
  }
}
data "terraform_remote_state" "platform" {
  backend = "s3"
  config = { bucket = var.state_bucket, key = var.platform_state_key, region = var.state_region
  }
}
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = merge({ Project = "RoundReady", Environment = var.environment, ManagedBy = "Terraform"
  }, var.common_tags)
}
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.tags
  }
}
module "rds" {
  source                        = "../../modules/rds"
  postgres_version              = var.postgres_version
  name_prefix                   = local.name_prefix
  vpc_id                        = data.terraform_remote_state.network.outputs.vpc_id
  private_data_subnet_ids       = data.terraform_remote_state.network.outputs.private_data_subnet_ids
  application_security_group_id = data.terraform_remote_state.platform.outputs.k3s_node_security_group_id
  production_mode               = var.environment == "production"
  instance_class                = var.rds_instance_class
  allocated_storage             = var.rds_allocated_storage
  max_allocated_storage         = var.rds_max_allocated_storage
  multi_az                      = var.rds_multi_az
  backup_retention_days         = var.rds_backup_retention_days
  deletion_protection           = var.rds_deletion_protection
  skip_final_snapshot           = var.rds_skip_final_snapshot
  apply_immediately             = var.rds_apply_immediately
  common_tags                   = local.tags
}
module "redis" {
  source                        = "../../modules/redis"
  engine                        = var.redis_engine
  engine_version                = var.redis_engine_version
  name_prefix                   = local.name_prefix
  vpc_id                        = data.terraform_remote_state.network.outputs.vpc_id
  private_data_subnet_ids       = data.terraform_remote_state.network.outputs.private_data_subnet_ids
  application_security_group_id = data.terraform_remote_state.platform.outputs.k3s_node_security_group_id
  production_mode               = var.environment == "production"
  node_type                     = var.redis_node_type
  replica_count                 = var.redis_replica_count
  multi_az                      = var.redis_multi_az
  snapshot_retention_days       = var.redis_snapshot_retention_days
  apply_immediately             = var.redis_apply_immediately
  secret_recovery_window_days   = var.managed_secret_recovery_window_days
  common_tags                   = local.tags
}
module "rabbitmq" {
  source                        = "../../modules/rabbitmq"
  engine_version                = var.rabbitmq_engine_version
  name_prefix                   = local.name_prefix
  vpc_id                        = data.terraform_remote_state.network.outputs.vpc_id
  private_data_subnet_ids       = data.terraform_remote_state.network.outputs.private_data_subnet_ids
  application_security_group_id = data.terraform_remote_state.platform.outputs.k3s_node_security_group_id
  production_mode               = var.environment == "production"
  instance_type                 = var.rabbitmq_instance_type
  deployment_mode               = var.rabbitmq_deployment_mode
  general_log_enabled           = var.rabbitmq_general_log_enabled
  apply_immediately             = var.rabbitmq_apply_immediately
  secret_recovery_window_days   = var.managed_secret_recovery_window_days
  common_tags                   = local.tags
}
output "rds_endpoint" {
  value = module.rds.endpoint
}
output "redis_endpoint" {
  value = module.redis.primary_endpoint
}
output "rabbitmq_endpoints" {
  value = module.rabbitmq.amqps_endpoints
}
