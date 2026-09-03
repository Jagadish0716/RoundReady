# IAM module

Creates one IAM role per AWS-dependent RoundReady workload. Trust is limited to the EKS Pod
Identity service and exact cluster ARN, namespace, and ServiceAccount request tags. Each inline
policy permits only `secretsmanager:DescribeSecret` and `secretsmanager:GetSecretValue` against its
explicit secret ARN list—there are no IAM users, access keys, shared workload role, wildcard secret
resources, or broad KMS permissions.

AWS supports creating Pod Identity associations before the corresponding ServiceAccounts exist,
so Terraform creates the AWS-side associations. The future workload deployment must create the
matching namespace and ServiceAccounts and install the EKS Pod Identity Agent; no Kubernetes
provider or manifest is owned here. Workers can use their parent service's ServiceAccount when
their secret needs are identical.
