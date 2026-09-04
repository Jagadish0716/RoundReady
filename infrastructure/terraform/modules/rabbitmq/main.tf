locals {
  broker_name = "${var.name_prefix}-rabbitmq"
  broker_subnet_ids = var.deployment_mode == "CLUSTER_MULTI_AZ" ? (
    slice(var.private_data_subnet_ids, 0, 3)
  ) : slice(var.private_data_subnet_ids, 0, 1)
  amqps_endpoints = [
    for endpoint in flatten([for instance in aws_mq_broker.this.instances : instance.endpoints]) :
    endpoint if startswith(endpoint, "amqps://")
  ]
}

resource "aws_security_group" "this" {
  name        = "${var.name_prefix}-rabbitmq"
  description = "AMQPS access from RoundReady application workloads"
  vpc_id      = var.vpc_id

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-rabbitmq" })
}

resource "aws_vpc_security_group_ingress_rule" "application" {
  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = var.application_security_group_id
  description                  = "AMQPS from EKS application security boundary"
  from_port                    = 5671
  to_port                      = 5671
  ip_protocol                  = "tcp"
}

resource "random_password" "broker" {
  length      = 48
  special     = false
  min_upper   = 12
  min_lower   = 12
  min_numeric = 12
}

resource "aws_secretsmanager_secret" "credentials" {
  name                    = "${var.name_prefix}/rabbitmq/credentials"
  description             = "RoundReady Amazon MQ RabbitMQ credentials"
  recovery_window_in_days = var.secret_recovery_window_days

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-rabbitmq-credentials" })
}

resource "aws_secretsmanager_secret_version" "credentials" {
  secret_id = aws_secretsmanager_secret.credentials.id
  secret_string = jsonencode({
    username     = var.username
    password     = random_password.broker.result
    rabbitmq_url = replace(local.amqps_endpoints[0], "amqps://", "amqps://${urlencode(var.username)}:${urlencode(random_password.broker.result)}@")
  })
}

resource "aws_mq_broker" "this" {
  broker_name        = local.broker_name
  engine_type        = "RabbitMQ"
  engine_version     = var.engine_version
  host_instance_type = var.instance_type
  deployment_mode    = var.deployment_mode

  publicly_accessible = false
  subnet_ids          = local.broker_subnet_ids
  security_groups     = [aws_security_group.this.id]

  authentication_strategy = "simple"
  user {
    username = var.username
    password = random_password.broker.result
  }

  encryption_options {
    use_aws_owned_key = true
  }

  logs {
    general = var.general_log_enabled
  }

  maintenance_window_start_time {
    day_of_week = var.maintenance_day
    time_of_day = var.maintenance_time
    time_zone   = "UTC"
  }

  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  apply_immediately          = var.apply_immediately

  lifecycle {
    precondition {
      condition = !var.production_mode || (
        var.deployment_mode == "CLUSTER_MULTI_AZ" &&
        length(var.private_data_subnet_ids) >= 3 &&
        var.secret_recovery_window_days >= 7
      )
      error_message = "Production RabbitMQ requires CLUSTER_MULTI_AZ, three private data subnets, and a recoverable credential secret."
    }
  }

  tags = merge(var.common_tags, { Name = local.broker_name })
}
