# VPC module

Creates one environment VPC with discovered Availability Zones, public subnets, private
application subnets, private data subnets, an Internet Gateway, and configurable NAT gateways.
Public subnets route to the Internet Gateway. Application subnets route to NAT; data subnets
have only the VPC-local route by default so RDS, ElastiCache, and Amazon MQ remain private.

Inputs: `name_prefix`, `vpc_cidr`, `az_count` (minimum 2), `nat_gateway_mode` (`one_per_az` or
`single`), `enable_flow_logs`, and `common_tags`. Subnet CIDRs are deterministically derived
from `vpc_cidr`; AZ names are never hardcoded. Public subnets receive
`kubernetes.io/role/elb=1`; application subnets receive
`kubernetes.io/role/internal-elb=1`. Cluster-specific tags belong to the future EKS module.

Production should use `one_per_az` and enable flow logs. Dev/staging may use `single` for cost,
with reduced NAT resilience. Flow logs use a minimal CloudWatch log group and IAM role and are
disabled by default. Future interface endpoints may include ECR API/DKR, S3, Secrets Manager,
CloudWatch Logs, and STS; they are deferred because each adds cost and route/security design.

This module deliberately uses default stateful network ACL behavior and creates no security
groups. Service modules own RDS, Redis, MQ, EKS, and ALB security groups and their least-
privilege ingress rules. No `0.0.0.0/0` inbound rule is introduced here.

Outputs: `vpc_id`, `vpc_cidr`, `public_subnet_ids`, `private_app_subnet_ids`, and
`private_data_subnet_ids`.
