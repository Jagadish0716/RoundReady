output "primary_endpoint" {
  description = "Primary Redis endpoint address without credentials."
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "reader_endpoint" {
  description = "Reader Redis endpoint address without credentials."
  value       = aws_elasticache_replication_group.this.reader_endpoint_address
}

output "port" {
  description = "TLS Redis protocol port."
  value       = aws_elasticache_replication_group.this.port
}

output "replication_group_id" {
  description = "ElastiCache replication group identifier."
  value       = aws_elasticache_replication_group.this.replication_group_id
}

output "security_group_id" {
  description = "Redis security group ID."
  value       = aws_security_group.this.id
}

output "credentials_secret_arn" {
  description = "Secrets Manager ARN containing the Redis auth token; no plaintext is exposed."
  value       = aws_secretsmanager_secret.credentials.arn
}
