# IAM module

Planned interface: least-privilege roles for EKS workloads, ECR pulls, Secrets Manager reads,
CloudWatch/OTLP integration, and deployment operations. Policies must be scoped by resource
and environment; credentials must not be embedded in Terraform outputs or tags.
