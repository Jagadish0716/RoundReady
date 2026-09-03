locals {
  replication_group_id = "${var.name_prefix}-redis"
}

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.name_prefix}-redis"
  subnet_ids = var.private_data_subnet_ids

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-redis" })
}

resource "aws_security_group" "this" {
  name        = "${var.name_prefix}-redis"
  description = "Redis protocol access from RoundReady application workloads"
  vpc_id      = var.vpc_id

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-redis" })
}

resource "aws_vpc_security_group_ingress_rule" "application" {
  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = var.application_security_group_id
  description                  = "TLS Redis protocol from EKS application security boundary"
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
}

resource "aws_kms_key" "this" {
  description             = "${var.name_prefix} ElastiCache encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-redis" })
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.name_prefix}-redis"
  target_key_id = aws_kms_key.this.key_id
}

resource "random_password" "auth_token" {
  length      = 48
  special     = false
  min_upper   = 12
  min_lower   = 12
  min_numeric = 12
}

resource "aws_secretsmanager_secret" "credentials" {
  name                    = "${var.name_prefix}/redis/credentials"
  description             = "RoundReady ElastiCache authentication token"
  recovery_window_in_days = var.secret_recovery_window_days

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-redis-credentials" })
}

resource "aws_secretsmanager_secret_version" "credentials" {
  secret_id = aws_secretsmanager_secret.credentials.id
  secret_string = jsonencode({
    auth_token = random_password.auth_token.result
  })
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = local.replication_group_id
  description          = "RoundReady managed Redis-compatible coordination store"

  engine         = var.engine
  engine_version = var.engine_version
  node_type      = var.node_type
  port           = 6379

  num_cache_clusters         = var.replica_count + 1
  automatic_failover_enabled = var.replica_count > 0
  multi_az_enabled           = var.multi_az

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = [aws_security_group.this.id]

  at_rest_encryption_enabled = true
  kms_key_id                 = aws_kms_key.this.arn
  transit_encryption_enabled = true
  transit_encryption_mode    = "required"
  auth_token                 = random_password.auth_token.result
  auth_token_update_strategy = "SET"

  snapshot_retention_limit   = var.snapshot_retention_days
  snapshot_window            = var.snapshot_window
  maintenance_window         = var.maintenance_window
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  apply_immediately          = var.apply_immediately

  lifecycle {
    precondition {
      condition = !var.production_mode || (
        var.multi_az &&
        var.replica_count >= 1 &&
        var.secret_recovery_window_days >= 7
      )
      error_message = "Production Redis requires Multi-AZ, at least one replica, and a recoverable credential secret."
    }
  }

  tags = merge(var.common_tags, { Name = local.replication_group_id })
}
