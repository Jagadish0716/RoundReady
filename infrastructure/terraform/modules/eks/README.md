# EKS module

Creates one version-pinned EKS control plane and one on-demand AWS-managed application node
group in the supplied private application subnets. Nodes are never placed in public or private
data subnets. The module does not deploy workloads, Helm releases, add-ons, or application IAM.

Inputs are `name_prefix`, `kubernetes_version`, `vpc_id`, `private_app_subnet_ids`, node instance
types/sizes/disk, public endpoint toggle/CIDRs, control-plane log toggle, optional operator IAM
principal ARNs, and `common_tags`. Private endpoint access is always enabled. Public access is
disabled by default and, when enabled, requires explicit CIDRs. Production examples disable it.

The cluster and node roles attach only the AWS-managed policies required for EKS control-plane,
VPC controller, node, CNI, and ECR pull operation. No AdministratorAccess or application IAM
permissions are granted. Kubernetes Secrets use a rotated, environment-scoped KMS key with
least-privilege cluster-role key permissions.

Operator principals use EKS access entries with a future `roundready:operators` RBAC group;
personal ARNs are not hardcoded. EKS Pod Identity is the preferred future workload IAM mechanism,
with application-specific associations deferred until workload definitions exist. The OIDC
issuer is exposed for compatibility with future integrations.

Control-plane logging supports API, audit, authenticator, controller manager, and scheduler logs.
Production enables all; development may disable them for cost. Cluster autoscaling add-ons and
AWS Load Balancer Controller are deferred. Initial production capacity is at least two on-demand
nodes across the VPC's private application AZs; future autoscaling and mixed Spot capacity can
be introduced after workload demand is measured.
