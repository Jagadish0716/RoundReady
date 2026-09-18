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
variable "kubernetes_version" {
  type = string
}
variable "node_instance_types" {
  type = list(string)
}
variable "node_min_size" {
  type = number
}
variable "node_desired_size" {
  type = number
}
variable "node_max_size" {
  type = number
}
variable "node_disk_size" {
  type = number
}
variable "enable_public_eks_endpoint" {
  type = bool
}
variable "eks_public_access_cidrs" {
  type = list(string)
}
variable "enable_eks_control_plane_logs" {
  type = bool
}
variable "eks_admin_principal_arns" {
  type = list(string)
}
variable "common_tags" {
  type = map(string)
}
variable "application_namespace" {
  type    = string
  default = "roundready"
}
variable "create_pod_identity_associations" {
  type    = bool
  default = true
}
data "aws_caller_identity" "current" {}
data "terraform_remote_state" "network" {
  backend = "s3"
  config = { bucket = var.state_bucket, key = var.network_state_key, region = var.state_region
  }
}
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = merge({ Project = "RoundReady", Environment = var.environment, ManagedBy = "Terraform"
  }, var.common_tags)
  secret_arn = { for key in ["auth-database", "user-database", "interviewer-database", "booking-database", "payment-database", "interview-database", "notification-database", "jwt-signing", "jwt-verification", "internal-identity", "internal-service", "razorpay", "livekit", "resend", "meta-whatsapp"] : key => "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}-${key}-*" }
  service_secret_arns = {
    api-gateway          = [local.secret_arn["jwt-verification"], local.secret_arn["internal-identity"], "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/redis/credentials-*"]
    auth-service         = [local.secret_arn["auth-database"], local.secret_arn["jwt-signing"], local.secret_arn["jwt-verification"], local.secret_arn["internal-identity"], "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/rabbitmq/credentials-*"]
    user-service         = [local.secret_arn["user-database"], local.secret_arn["internal-identity"], local.secret_arn["internal-service"]]
    interviewer-service  = [local.secret_arn["interviewer-database"], local.secret_arn["internal-identity"], "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/rabbitmq/credentials-*"]
    booking-service      = [local.secret_arn["booking-database"], local.secret_arn["internal-identity"], "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/redis/credentials-*", "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/rabbitmq/credentials-*"]
    payment-service      = [local.secret_arn["payment-database"], local.secret_arn["internal-identity"], local.secret_arn["razorpay"], "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/rabbitmq/credentials-*"]
    interview-service    = [local.secret_arn["interview-database"], local.secret_arn["internal-identity"], local.secret_arn["livekit"], "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/rabbitmq/credentials-*"]
    notification-service = [local.secret_arn["notification-database"], local.secret_arn["internal-identity"], local.secret_arn["internal-service"], local.secret_arn["resend"], local.secret_arn["meta-whatsapp"], "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/rabbitmq/credentials-*"]
  }
}
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.tags
  }
}
module "eks" {
  source                    = "../../modules/eks"
  name_prefix               = local.name_prefix
  kubernetes_version        = var.kubernetes_version
  vpc_id                    = data.terraform_remote_state.network.outputs.vpc_id
  private_app_subnet_ids    = data.terraform_remote_state.network.outputs.private_app_subnet_ids
  node_instance_types       = var.node_instance_types
  node_min_size             = var.node_min_size
  node_desired_size         = var.node_desired_size
  node_max_size             = var.node_max_size
  node_disk_size            = var.node_disk_size
  enable_public_endpoint    = var.enable_public_eks_endpoint
  public_access_cidrs       = var.eks_public_access_cidrs
  enable_control_plane_logs = var.enable_eks_control_plane_logs
  admin_principal_arns      = var.eks_admin_principal_arns
  common_tags               = local.tags
}
module "iam" {
  source                           = "../../modules/iam"
  name_prefix                      = local.name_prefix
  cluster_name                     = module.eks.cluster_name
  cluster_arn                      = module.eks.cluster_arn
  namespace                        = var.application_namespace
  service_secret_arns              = local.service_secret_arns
  create_pod_identity_associations = var.create_pod_identity_associations
  common_tags                      = local.tags
}
output "cluster_name" {
  value = module.eks.cluster_name
}
output "cluster_arn" {
  value = module.eks.cluster_arn
}
output "cluster_security_group_id" {
  value = module.eks.cluster_security_group_id
}
output "workload_iam_role_arns" {
  value = module.iam.workload_role_arns
}
output "pod_identity_association_arns" {
  value = module.iam.pod_identity_association_arns
}
