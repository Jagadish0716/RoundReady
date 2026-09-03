output "broker_id" {
  description = "Amazon MQ broker ID."
  value       = aws_mq_broker.this.id
}

output "broker_arn" {
  description = "Amazon MQ broker ARN."
  value       = aws_mq_broker.this.arn
}

output "amqps_endpoints" {
  description = "Private AMQPS endpoints without credentials."
  value = [
    for endpoint in flatten([for instance in aws_mq_broker.this.instances : instance.endpoints]) :
    endpoint if startswith(endpoint, "amqps://")
  ]
}

output "security_group_id" {
  description = "Amazon MQ security group ID."
  value       = aws_security_group.this.id
}

output "credentials_secret_arn" {
  description = "Secrets Manager ARN containing RabbitMQ credentials; no plaintext is exposed."
  value       = aws_secretsmanager_secret.credentials.arn
}
