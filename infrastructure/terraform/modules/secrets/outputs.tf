output "secret_arns" {
  description = "Secret-container ARNs keyed by logical purpose; no values or versions are exposed."
  value       = { for key, secret in aws_secretsmanager_secret.this : key => secret.arn }
}
