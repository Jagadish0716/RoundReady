terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }
  backend "s3" { use_lockfile = true }
}
variable "aws_region" { type = string }
variable "environment" { type = string }
variable "project_name" { type = string }
variable "state_bucket" { type = string }
variable "state_region" { type = string }
variable "network_state_key" { type = string }
variable "platform_state_key" { type = string }
variable "frontend_target_port" { type = number }
variable "frontend_health_check_path" { type = string }
variable "common_tags" { type = map(string) }
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags        = merge({ Project = "RoundReady", Environment = var.environment, ManagedBy = "Terraform" }, var.common_tags)
}
provider "aws" {
  region = var.aws_region
  default_tags { tags = local.tags }
}
data "terraform_remote_state" "network" {
  backend = "s3"
  config  = { bucket = var.state_bucket, key = var.network_state_key, region = var.state_region }
}
data "terraform_remote_state" "platform" {
  backend = "s3"
  config  = { bucket = var.state_bucket, key = var.platform_state_key, region = var.state_region }
}
module "alb" {
  source                     = "../../modules/k3s-alb"
  name_prefix                = local.name_prefix
  vpc_id                     = data.terraform_remote_state.network.outputs.vpc_id
  public_subnet_ids          = data.terraform_remote_state.network.outputs.public_subnet_ids
  k3s_node_security_group_id = data.terraform_remote_state.platform.outputs.k3s_node_security_group_id
  k3s_instance_ids = [
    data.terraform_remote_state.platform.outputs.k3s_server_instance_id,
    data.terraform_remote_state.platform.outputs.k3s_worker_instance_id,
  ]
  target_port       = var.frontend_target_port
  health_check_path = var.frontend_health_check_path
  common_tags       = local.tags
}
output "alb_dns_name" { value = module.alb.alb_dns_name }
output "alb_zone_id" { value = module.alb.alb_zone_id }
output "alb_security_group_id" { value = module.alb.alb_security_group_id }
output "frontend_target_group_arn" { value = module.alb.target_group_arn }
