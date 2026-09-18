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
variable "managed_secret_recovery_window_days" {
  type = number
}
variable "application_log_retention_days" {
  type = number
}
variable "common_tags" {
  type = map(string)
}
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = merge({ Project = "RoundReady", Environment = var.environment, ManagedBy = "Terraform"
  }, var.common_tags)
  secrets = { for key in ["auth_database", "user_database", "interviewer_database", "booking_database", "payment_database", "interview_database", "notification_database", "jwt_signing", "jwt_verification", "internal_identity", "internal_service", "razorpay", "livekit", "resend", "meta_whatsapp"] : key => { description = "RoundReady ${replace(key, "_", " ")} secret container", owner = "roundready"
    }
  }
}
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.tags
  }
}
module "secrets" {
  source               = "../../modules/secrets"
  name_prefix          = local.name_prefix
  secrets              = local.secrets
  recovery_window_days = var.managed_secret_recovery_window_days
  common_tags          = local.tags
}
module "observability" {
  source                          = "../../modules/observability"
  name_prefix                     = local.name_prefix
  environment                     = var.environment
  application_log_retention_days  = var.application_log_retention_days
  aws_native_alarms_enabled       = false
  rds_instance_identifier         = "${local.name_prefix}-postgres"
  rds_cpu_alarm_threshold_percent = 80
  rds_free_storage_alarm_bytes    = 10737418240
  common_tags                     = local.tags
}
output "application_secret_arns" {
  value = module.secrets.secret_arns
}
output "application_log_group_name" {
  value = module.observability.application_log_group_name
}
