output "endpoint" {
  description = "RDS endpoint including the PostgreSQL port."
  value       = aws_db_instance.this.endpoint
}

output "address" {
  description = "RDS DNS address without credentials."
  value       = aws_db_instance.this.address
}

output "port" {
  description = "PostgreSQL listener port."
  value       = aws_db_instance.this.port
}

output "instance_identifier" {
  description = "RDS DB instance identifier."
  value       = aws_db_instance.this.identifier
}

output "security_group_id" {
  description = "RDS security group ID."
  value       = aws_security_group.this.id
}

output "subnet_group_name" {
  description = "Private RDS subnet group name."
  value       = aws_db_subnet_group.this.name
}

output "master_secret_arn" {
  description = "ARN of the AWS-managed master credential secret; no secret value is exposed."
  value       = aws_db_instance.this.master_user_secret[0].secret_arn
}
