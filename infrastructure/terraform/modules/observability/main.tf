resource "aws_cloudwatch_log_group" "applications" {
  name              = "/roundready/${var.environment}/applications"
  retention_in_days = var.application_log_retention_days

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-applications" })
}

resource "aws_sns_topic" "alarms" {
  count             = var.aws_native_alarms_enabled ? 1 : 0
  name              = "${var.name_prefix}-infrastructure-alarms"
  kms_master_key_id = "alias/aws/sns"

  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  count = var.aws_native_alarms_enabled ? 1 : 0

  alarm_name          = "${var.name_prefix}-rds-cpu-high"
  alarm_description   = "RDS CPU utilization is above the initial operational threshold."
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  dimensions          = { DBInstanceIdentifier = var.rds_instance_identifier }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.rds_cpu_alarm_threshold_percent
  treat_missing_data  = "missing"
  alarm_actions       = [aws_sns_topic.alarms[0].arn]
  ok_actions          = [aws_sns_topic.alarms[0].arn]

  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage_low" {
  count = var.aws_native_alarms_enabled ? 1 : 0

  alarm_name          = "${var.name_prefix}-rds-free-storage-low"
  alarm_description   = "RDS free storage is below the initial operational threshold."
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  dimensions          = { DBInstanceIdentifier = var.rds_instance_identifier }
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  comparison_operator = "LessThanThreshold"
  threshold           = var.rds_free_storage_alarm_bytes
  treat_missing_data  = "missing"
  alarm_actions       = [aws_sns_topic.alarms[0].arn]
  ok_actions          = [aws_sns_topic.alarms[0].arn]

  tags = var.common_tags
}
