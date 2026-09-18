terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" { use_lockfile = true }
}
variable "aws_region" { type = string }
variable "environment" { type = string }
variable "project_name" { type = string }
variable "vpc_cidr" { type = string }
variable "az_count" { type = number }
variable "nat_gateway_mode" { type = string }
variable "enable_flow_logs" { type = bool }
variable "common_tags" { type = map(string) }
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags        = merge({ Project = "RoundReady", Environment = var.environment, ManagedBy = "Terraform" }, var.common_tags)
}
provider "aws" {
  region = var.aws_region
  default_tags { tags = local.tags }
}
module "vpc" {
  source           = "../../modules/vpc"
  name_prefix      = local.name_prefix
  vpc_cidr         = var.vpc_cidr
  az_count         = var.az_count
  nat_gateway_mode = var.nat_gateway_mode
  enable_flow_logs = var.enable_flow_logs
  common_tags      = local.tags
}
output "vpc_id" { value = module.vpc.vpc_id }
output "vpc_cidr" { value = module.vpc.vpc_cidr }
output "public_subnet_ids" { value = module.vpc.public_subnet_ids }
output "private_app_subnet_ids" { value = module.vpc.private_app_subnet_ids }
output "private_data_subnet_ids" { value = module.vpc.private_data_subnet_ids }
