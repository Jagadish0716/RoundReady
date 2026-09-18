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
variable "state_bucket" { type = string }
variable "state_region" { type = string }
variable "platform_state_key" { type = string }
variable "enabled" {
  type = bool
}
variable "controller_version" {
  type = string
}
variable "public_ingress_enabled" {
  type = bool
}
variable "hosted_zone_id" {
  type    = string
  default = null
}
variable "hosted_zone_name" {
  type    = string
  default = null
}
variable "frontend_domain" {
  type    = string
  default = null
}
variable "api_domain" {
  type    = string
  default = null
}
variable "public_alb_dns_name" {
  type    = string
  default = null
}
variable "public_alb_zone_id" {
  type    = string
  default = null
}
variable "common_tags" {
  type = map(string)
}
data "terraform_remote_state" "platform" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = var.platform_state_key
    region = var.state_region
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
module "alb" {
  source             = "../../modules/alb"
  enabled            = var.enabled
  name_prefix        = local.name_prefix
  cluster_name       = data.terraform_remote_state.platform.outputs.cluster_name
  controller_version = var.controller_version
  common_tags        = local.tags
}
module "dns" {
  source           = "../../modules/dns"
  enabled          = var.public_ingress_enabled
  name_prefix      = local.name_prefix
  hosted_zone_id   = var.hosted_zone_id
  hosted_zone_name = var.hosted_zone_name
  frontend_domain  = var.frontend_domain
  api_domain       = var.api_domain
  alb_dns_name     = var.public_alb_dns_name
  alb_zone_id      = var.public_alb_zone_id
  common_tags      = local.tags
}
output "controller_role_arn" {
  value = module.alb.controller_iam_role_arn
}
output "certificate_arn" {
  value = module.dns.certificate_arn
}
