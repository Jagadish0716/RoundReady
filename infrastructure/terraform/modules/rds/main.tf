locals {
  identifier = "${var.name_prefix}-postgres"
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-postgres"
  subnet_ids = var.private_data_subnet_ids

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-postgres" })
}

resource "aws_security_group" "this" {
  name        = "${var.name_prefix}-postgres"
  description = "PostgreSQL access from RoundReady application workloads"
  vpc_id      = var.vpc_id

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-postgres" })
}

resource "aws_vpc_security_group_ingress_rule" "application" {
  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = var.application_security_group_id
  description                  = "PostgreSQL from EKS application security boundary"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_kms_key" "this" {
  description             = "${var.name_prefix} RDS PostgreSQL encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-rds" })
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.name_prefix}-rds"
  target_key_id = aws_kms_key.this.key_id
}

resource "aws_iam_role" "enhanced_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0
  name  = "${var.name_prefix}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "enhanced_monitoring" {
  count      = var.monitoring_interval > 0 ? 1 : 0
  role       = aws_iam_role.enhanced_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

resource "aws_db_instance" "this" {
  identifier = local.identifier

  engine                        = "postgres"
  engine_version                = var.postgres_version
  instance_class                = var.instance_class
  port                          = 5432
  username                      = var.master_username
  manage_master_user_password   = true
  master_user_secret_kms_key_id = aws_kms_key.this.key_id

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.this.arn

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.this.id]
  publicly_accessible    = false
  multi_az               = var.multi_az

  backup_retention_period   = var.backup_retention_days
  backup_window             = var.backup_window
  maintenance_window        = var.maintenance_window
  copy_tags_to_snapshot     = true
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.identifier}-final"

  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  apply_immediately          = var.apply_immediately

  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_kms_key_id       = var.performance_insights_enabled ? aws_kms_key.this.arn : null
  performance_insights_retention_period = var.performance_insights_enabled ? var.performance_insights_retention_days : null

  monitoring_interval = var.monitoring_interval
  monitoring_role_arn = var.monitoring_interval > 0 ? aws_iam_role.enhanced_monitoring[0].arn : null

  enabled_cloudwatch_logs_exports = var.cloudwatch_log_exports

  lifecycle {
    precondition {
      condition     = var.max_allocated_storage >= var.allocated_storage
      error_message = "max_allocated_storage must be greater than or equal to allocated_storage."
    }

    precondition {
      condition = !var.production_mode || (
        var.multi_az &&
        var.deletion_protection &&
        !var.skip_final_snapshot &&
        var.backup_retention_days >= 7
      )
      error_message = "Production RDS requires Multi-AZ, deletion protection, a final snapshot, and at least seven days of backups."
    }
  }

  depends_on = [aws_iam_role_policy_attachment.enhanced_monitoring]

  tags = merge(var.common_tags, { Name = local.identifier })
}
