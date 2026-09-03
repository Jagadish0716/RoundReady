data "aws_caller_identity" "current" {}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  deployable_components = [
    "api-gateway",
    "auth-service",
    "user-service",
    "interviewer-service",
    "booking-service",
    "payment-service",
    "interview-service",
    "notification-service",
    "frontend",
  ]
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

  name_prefix      = local.name_prefix
  vpc_cidr         = var.vpc_cidr
  az_count         = var.az_count
  nat_gateway_mode = var.nat_gateway_mode
  enable_flow_logs = var.enable_flow_logs
  common_tags      = local.common_tags
}

module "eks" {
  source = "./modules/eks"

  name_prefix               = local.name_prefix
  kubernetes_version        = var.kubernetes_version
  vpc_id                    = module.vpc.vpc_id
  private_app_subnet_ids    = module.vpc.private_app_subnet_ids
  node_instance_types       = var.node_instance_types
  node_min_size             = var.node_min_size
  node_desired_size         = var.node_desired_size
  node_max_size             = var.node_max_size
  node_disk_size            = var.node_disk_size
  enable_public_endpoint    = var.enable_public_eks_endpoint
  public_access_cidrs       = var.eks_public_access_cidrs
  enable_control_plane_logs = var.enable_eks_control_plane_logs
  admin_principal_arns      = var.eks_admin_principal_arns
  common_tags               = local.common_tags
}

module "rds" {
  source = "./modules/rds"

  name_prefix                   = local.name_prefix
  vpc_id                        = module.vpc.vpc_id
  private_data_subnet_ids       = module.vpc.private_data_subnet_ids
  application_security_group_id = module.eks.cluster_security_group_id
  production_mode               = var.environment == "production"
  postgres_version              = var.rds_postgres_version
  instance_class                = var.rds_instance_class
  allocated_storage             = var.rds_allocated_storage
  max_allocated_storage         = var.rds_max_allocated_storage
  multi_az                      = var.rds_multi_az
  backup_retention_days         = var.rds_backup_retention_days
  deletion_protection           = var.rds_deletion_protection
  skip_final_snapshot           = var.rds_skip_final_snapshot
  apply_immediately             = var.rds_apply_immediately
  performance_insights_enabled  = var.rds_performance_insights_enabled
  monitoring_interval           = var.rds_monitoring_interval
  cloudwatch_log_exports        = var.rds_cloudwatch_log_exports
  common_tags                   = local.common_tags
}

module "redis" {
  source = "./modules/redis"

  name_prefix                   = local.name_prefix
  vpc_id                        = module.vpc.vpc_id
  private_data_subnet_ids       = module.vpc.private_data_subnet_ids
  application_security_group_id = module.eks.cluster_security_group_id
  production_mode               = var.environment == "production"
  engine                        = var.redis_engine
  engine_version                = var.redis_engine_version
  node_type                     = var.redis_node_type
  replica_count                 = var.redis_replica_count
  multi_az                      = var.redis_multi_az
  snapshot_retention_days       = var.redis_snapshot_retention_days
  apply_immediately             = var.redis_apply_immediately
  secret_recovery_window_days   = var.managed_secret_recovery_window_days
  common_tags                   = local.common_tags
}

module "rabbitmq" {
  source = "./modules/rabbitmq"

  name_prefix                   = local.name_prefix
  vpc_id                        = module.vpc.vpc_id
  private_data_subnet_ids       = module.vpc.private_data_subnet_ids
  application_security_group_id = module.eks.cluster_security_group_id
  production_mode               = var.environment == "production"
  engine_version                = var.rabbitmq_engine_version
  instance_type                 = var.rabbitmq_instance_type
  deployment_mode               = var.rabbitmq_deployment_mode
  general_log_enabled           = var.rabbitmq_general_log_enabled
  apply_immediately             = var.rabbitmq_apply_immediately
  secret_recovery_window_days   = var.managed_secret_recovery_window_days
  common_tags                   = local.common_tags
}

module "alb" {
  source = "./modules/alb"

  enabled            = var.load_balancer_controller_enabled
  name_prefix        = local.name_prefix
  cluster_name       = module.eks.cluster_name
  controller_version = var.load_balancer_controller_version
  common_tags        = local.common_tags
}

module "dns" {
  source = "./modules/dns"

  enabled          = var.public_ingress_enabled
  name_prefix      = local.name_prefix
  hosted_zone_id   = var.hosted_zone_id
  hosted_zone_name = var.hosted_zone_name
  frontend_domain  = var.frontend_domain
  api_domain       = var.api_domain
  common_tags      = local.common_tags
}

locals {
  application_secret_definitions = {
    auth_database = {
      description = "Auth service-owned PostgreSQL connection configuration"
      owner       = "auth-service"
    }
    user_database = {
      description = "User service-owned PostgreSQL connection configuration"
      owner       = "user-service"
    }
    interviewer_database = {
      description = "Interviewer service-owned PostgreSQL connection configuration"
      owner       = "interviewer-service"
    }
    booking_database = {
      description = "Booking service-owned PostgreSQL connection configuration"
      owner       = "booking-service"
    }
    payment_database = {
      description = "Payment service-owned PostgreSQL connection configuration"
      owner       = "payment-service"
    }
    interview_database = {
      description = "Interview service-owned PostgreSQL connection configuration"
      owner       = "interview-service"
    }
    notification_database = {
      description = "Notification service-owned PostgreSQL connection configuration"
      owner       = "notification-service"
    }
    jwt_signing = {
      description = "Auth-service JWT signing material"
      owner       = "auth-service"
    }
    jwt_verification = {
      description = "JWT verification material shared with the gateway"
      owner       = "auth-service"
    }
    internal_identity = {
      description = "Gateway-to-service trusted identity credential"
      owner       = "platform"
    }
    internal_service = {
      description = "Notification-to-user internal API credential"
      owner       = "platform"
    }
    razorpay = {
      description = "Razorpay production API and webhook credentials"
      owner       = "payment-service"
    }
    livekit = {
      description = "LiveKit production API credentials"
      owner       = "interview-service"
    }
    resend = {
      description = "Resend production email credential"
      owner       = "notification-service"
    }
    meta_whatsapp = {
      description = "Meta WhatsApp Cloud API production credentials"
      owner       = "notification-service"
    }
  }
}

module "secrets" {
  source = "./modules/secrets"

  name_prefix          = local.name_prefix
  secrets              = local.application_secret_definitions
  recovery_window_days = var.managed_secret_recovery_window_days
  common_tags          = local.common_tags
}

locals {
  service_secret_arns = {
    api-gateway = [
      module.secrets.secret_arns["jwt_verification"],
      module.secrets.secret_arns["internal_identity"],
      module.redis.credentials_secret_arn,
    ]
    auth-service = [
      module.secrets.secret_arns["auth_database"],
      module.secrets.secret_arns["jwt_signing"],
      module.secrets.secret_arns["jwt_verification"],
      module.secrets.secret_arns["internal_identity"],
      module.rabbitmq.credentials_secret_arn,
    ]
    user-service = [
      module.secrets.secret_arns["user_database"],
      module.secrets.secret_arns["internal_identity"],
      module.secrets.secret_arns["internal_service"],
    ]
    interviewer-service = [
      module.secrets.secret_arns["interviewer_database"],
      module.secrets.secret_arns["internal_identity"],
      module.rabbitmq.credentials_secret_arn,
    ]
    booking-service = [
      module.secrets.secret_arns["booking_database"],
      module.secrets.secret_arns["internal_identity"],
      module.redis.credentials_secret_arn,
      module.rabbitmq.credentials_secret_arn,
    ]
    payment-service = [
      module.secrets.secret_arns["payment_database"],
      module.secrets.secret_arns["internal_identity"],
      module.secrets.secret_arns["razorpay"],
      module.rabbitmq.credentials_secret_arn,
    ]
    interview-service = [
      module.secrets.secret_arns["interview_database"],
      module.secrets.secret_arns["internal_identity"],
      module.secrets.secret_arns["livekit"],
      module.rabbitmq.credentials_secret_arn,
    ]
    notification-service = [
      module.secrets.secret_arns["notification_database"],
      module.secrets.secret_arns["internal_identity"],
      module.secrets.secret_arns["internal_service"],
      module.secrets.secret_arns["resend"],
      module.secrets.secret_arns["meta_whatsapp"],
      module.rabbitmq.credentials_secret_arn,
    ]
  }
}

module "iam" {
  source = "./modules/iam"

  name_prefix                      = local.name_prefix
  cluster_name                     = module.eks.cluster_name
  cluster_arn                      = module.eks.cluster_arn
  namespace                        = var.application_namespace
  service_secret_arns              = local.service_secret_arns
  create_pod_identity_associations = var.create_pod_identity_associations
  common_tags                      = local.common_tags
}

module "ecr" {
  source = "./modules/ecr"

  name_prefix                  = local.name_prefix
  production_mode              = var.environment == "production"
  components                   = local.deployable_components
  image_tag_mutability         = var.ecr_image_tag_mutability
  scan_on_push                 = var.ecr_scan_on_push
  tagged_image_retention_count = var.ecr_tagged_image_retention_count
  untagged_retention_days      = var.ecr_untagged_retention_days
  force_delete                 = var.ecr_force_delete
  common_tags                  = local.common_tags
}

module "observability" {
  source = "./modules/observability"

  name_prefix                     = local.name_prefix
  environment                     = var.environment
  application_log_retention_days  = var.application_log_retention_days
  aws_native_alarms_enabled       = var.aws_native_alarms_enabled
  rds_instance_identifier         = module.rds.instance_identifier
  rds_cpu_alarm_threshold_percent = var.rds_cpu_alarm_threshold_percent
  rds_free_storage_alarm_bytes    = var.rds_free_storage_alarm_bytes
  common_tags                     = local.common_tags
}
