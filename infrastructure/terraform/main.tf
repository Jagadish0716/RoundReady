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
  ecr_components = [
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
  application_secret_definitions = {
    auth_database        = { description = "Auth service PostgreSQL configuration", owner = "auth-service" }
    user_database        = { description = "User service PostgreSQL configuration", owner = "user-service" }
    interviewer_database = { description = "Interviewer service PostgreSQL configuration", owner = "interviewer-service" }
    booking_database     = { description = "Booking service PostgreSQL configuration", owner = "booking-service" }
    payment_database     = { description = "Payment service PostgreSQL configuration", owner = "payment-service" }
    interview_database   = { description = "Interview service PostgreSQL configuration", owner = "interview-service" }
    notification_database = {
      description = "Notification service PostgreSQL configuration"
      owner       = "notification-service"
    }
    jwt_signing      = { description = "Auth-service JWT signing material", owner = "auth-service" }
    jwt_verification = { description = "JWT verification material shared with the gateway", owner = "auth-service" }
    internal_identity = {
      description = "Gateway-to-service trusted identity credential"
      owner       = "platform"
    }
    internal_service = {
      description = "Notification-to-user internal API credential"
      owner       = "platform"
    }
    razorpay      = { description = "Razorpay API and webhook credentials", owner = "payment-service" }
    livekit       = { description = "LiveKit API credentials", owner = "interview-service" }
    resend        = { description = "Resend email credential", owner = "notification-service" }
    meta_whatsapp = { description = "Meta WhatsApp Cloud API credentials", owner = "notification-service" }
  }
}

module "network" {
  source = "./modules/vpc"

  name_prefix      = local.name_prefix
  vpc_cidr         = var.vpc_cidr
  az_count         = var.az_count
  nat_gateway_mode = var.nat_gateway_mode
  enable_flow_logs = var.enable_flow_logs
  common_tags      = local.common_tags
}

module "ecr" {
  source = "./modules/ecr"

  name_prefix                  = local.name_prefix
  production_mode              = var.environment == "production"
  components                   = local.ecr_components
  image_tag_mutability         = var.ecr_image_tag_mutability
  scan_on_push                 = var.ecr_scan_on_push
  tagged_image_retention_count = var.ecr_tagged_image_retention_count
  untagged_retention_days      = var.ecr_untagged_retention_days
  force_delete                 = var.ecr_force_delete
  common_tags                  = local.common_tags
}

module "k3s" {
  source = "./modules/k3s"

  name_prefix            = local.name_prefix
  aws_region             = var.aws_region
  vpc_id                 = module.network.vpc_id
  private_app_subnet_ids = module.network.private_app_subnet_ids
  instance_type          = var.k3s_instance_type
  root_volume_size       = var.k3s_root_volume_size
  ami_ssm_parameter      = var.k3s_ami_ssm_parameter
  ec2_key_name           = var.ec2_key_name
  ecr_repository_arns    = values(module.ecr.repository_arns)
  common_tags            = local.common_tags
}

module "rds" {
  source = "./modules/rds"

  name_prefix                   = local.name_prefix
  vpc_id                        = module.network.vpc_id
  private_data_subnet_ids       = module.network.private_data_subnet_ids
  application_security_group_id = module.k3s.security_group_id
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
  vpc_id                        = module.network.vpc_id
  private_data_subnet_ids       = module.network.private_data_subnet_ids
  application_security_group_id = module.k3s.security_group_id
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
  vpc_id                        = module.network.vpc_id
  private_data_subnet_ids       = module.network.private_data_subnet_ids
  application_security_group_id = module.k3s.security_group_id
  production_mode               = var.environment == "production"
  engine_version                = var.rabbitmq_engine_version
  instance_type                 = var.rabbitmq_instance_type
  deployment_mode               = var.rabbitmq_deployment_mode
  general_log_enabled           = var.rabbitmq_general_log_enabled
  apply_immediately             = var.rabbitmq_apply_immediately
  secret_recovery_window_days   = var.managed_secret_recovery_window_days
  common_tags                   = local.common_tags
}

module "secrets" {
  source = "./modules/secrets"

  name_prefix          = local.name_prefix
  secrets              = local.application_secret_definitions
  recovery_window_days = var.managed_secret_recovery_window_days
  common_tags          = local.common_tags
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

module "k3s_alb" {
  source = "./modules/k3s-alb"

  name_prefix                = local.name_prefix
  vpc_id                     = module.network.vpc_id
  public_subnet_ids          = module.network.public_subnet_ids
  k3s_node_security_group_id = module.k3s.security_group_id
  k3s_instance_ids = [
    module.k3s.server_instance_id,
    module.k3s.worker_instance_id,
  ]
  target_port       = 30080
  health_check_path = "/"
  common_tags       = local.common_tags
}
