data "aws_caller_identity" "current" {}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = merge(
    {
      Project     = "RoundReady"
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.common_tags,
  )
}

module "vpc" {
  source = "./modules/vpc"

  name_prefix        = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  az_count           = var.az_count
  nat_gateway_mode   = var.nat_gateway_mode
  enable_flow_logs   = var.enable_flow_logs
  common_tags        = local.common_tags
}

module "eks" {
  source = "./modules/eks"

  name_prefix                = local.name_prefix
  kubernetes_version         = var.kubernetes_version
  vpc_id                     = module.vpc.vpc_id
  private_app_subnet_ids     = module.vpc.private_app_subnet_ids
  node_instance_types        = var.node_instance_types
  node_min_size              = var.node_min_size
  node_desired_size          = var.node_desired_size
  node_max_size              = var.node_max_size
  node_disk_size             = var.node_disk_size
  enable_public_endpoint     = var.enable_public_eks_endpoint
  public_access_cidrs        = var.eks_public_access_cidrs
  enable_control_plane_logs  = var.enable_eks_control_plane_logs
  admin_principal_arns       = var.eks_admin_principal_arns
  common_tags                = local.common_tags
}