output "application_log_group_name" {
  description = "Shared application CloudWatch log-group name."
  value       = aws_cloudwatch_log_group.applications.name
}

output "application_log_group_arn" {
  description = "Shared application CloudWatch log-group ARN."
  value       = aws_cloudwatch_log_group.applications.arn
}

output "alarm_topic_arn" {
  description = "Optional unsubscribed SNS topic ARN for future alarm integrations."
  value       = var.aws_native_alarms_enabled ? aws_sns_topic.alarms[0].arn : null
}

output "alarm_arns" {
  description = "AWS-native alarm ARNs keyed by purpose."
  value = var.aws_native_alarms_enabled ? {
    rds_cpu_high         = aws_cloudwatch_metric_alarm.rds_cpu_high[0].arn
    rds_free_storage_low = aws_cloudwatch_metric_alarm.rds_free_storage_low[0].arn
  } : {}
}
