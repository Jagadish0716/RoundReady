# RoundReady Terraform foundation

This directory is the 14I.1 foundation for the planned AWS production platform. It intentionally
contains no billable AWS resources. The root validates shared naming, tags, region input, and
runtime AWS account discovery; resource modules are added only after their interfaces and
security designs are reviewed.

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
5. Review a plan before any future apply. This 14I.1 change must not be applied.

No account IDs, bucket names, credentials, or secret values are committed. AWS provider
credentials and region are supplied by the operator/runtime environment.
