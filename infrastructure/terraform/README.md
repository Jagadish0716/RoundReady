# RoundReady Terraform foundation

This directory defines the AWS foundation for RoundReady. Its VPC, EKS, RDS,
ElastiCache, Amazon MQ, ECR, Secrets Manager, DNS/ACM, IAM, and CloudWatch
resources are billable when applied. The root validates shared naming, tags,
region input, environment safeguards, and runtime AWS account discovery.

## Layout

- `environments/` contains independent dev, staging, and production inputs/state guidance.
- `modules/` contains ownership/interface READMEs for VPC, EKS, ECR, RDS, Redis, Amazon MQ,
  IAM, Secrets Manager, ALB, DNS/ACM, and observability.
- `versions.tf`, `variables.tf`, `main.tf`, and `outputs.tf` define the shared foundation.

## Safe workflow

1. Bootstrap the encrypted, versioned S3 state bucket and IAM access outside
   this root.
2. Select one environment's variables and an environment-specific state key.
3. Run `terraform init` with backend configuration supplied at runtime.
4. Run `terraform fmt -check` and `terraform validate`.
5. Review resources, safeguards, and estimated cost before any apply; deploy dev first.

The complete DEV-first infrastructure-to-application dependency sequence is in
`docs/aws-deployment-runbook.md`.

No account IDs, bucket names, credentials, or secret values are committed. AWS provider
credentials and region are supplied by the operator/runtime environment.
