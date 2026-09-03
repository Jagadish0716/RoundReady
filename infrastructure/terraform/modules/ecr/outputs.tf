output "repository_names" {
  description = "Private ECR repository names keyed by component."
  value       = { for component, repository in aws_ecr_repository.this : component => repository.name }
}

output "repository_arns" {
  description = "Private ECR repository ARNs keyed by component."
  value       = { for component, repository in aws_ecr_repository.this : component => repository.arn }
}

output "repository_urls" {
  description = "Private ECR repository URLs keyed by component; no credentials are included."
  value       = { for component, repository in aws_ecr_repository.this : component => repository.repository_url }
}
