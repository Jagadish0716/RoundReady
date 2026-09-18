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
variable "common_tags" { type = map(string) }
variable "ecr_image_tag_mutability" { type = string }
variable "ecr_scan_on_push" { type = bool }
variable "ecr_tagged_image_retention_count" { type = number }
variable "ecr_untagged_retention_days" { type = number }
variable "ecr_force_delete" { type = bool }
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags        = merge({ Project = "RoundReady", Environment = var.environment, ManagedBy = "Terraform" }, var.common_tags)
  components  = ["api-gateway", "auth-service", "user-service", "interviewer-service", "booking-service", "payment-service", "interview-service", "notification-service", "frontend"]
}
provider "aws" {
  region = var.aws_region
  default_tags { tags = local.tags }
}
module "ecr" {
  source                       = "../../modules/ecr"
  name_prefix                  = local.name_prefix
  production_mode              = var.environment == "production"
  components                   = local.components
  image_tag_mutability         = var.ecr_image_tag_mutability
  scan_on_push                 = var.ecr_scan_on_push
  tagged_image_retention_count = var.ecr_tagged_image_retention_count
  untagged_retention_days      = var.ecr_untagged_retention_days
  force_delete                 = var.ecr_force_delete
  common_tags                  = local.tags
}
output "ecr_repository_urls" { value = module.ecr.repository_urls }
output "ecr_repository_arns" { value = module.ecr.repository_arns }
