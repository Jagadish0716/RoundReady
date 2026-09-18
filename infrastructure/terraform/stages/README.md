# Staged AWS deployment

`01-network` is the first independent root and owns only the VPC module. Its
remote-state outputs are the contract for later platform and data roots.

```bash
terraform -chdir=infrastructure/terraform/stages/01-network init -backend-config="bucket=$TF_STATE_BUCKET" -backend-config="key=roundready/dev/01-network.tfstate" -backend-config="region=ap-south-1" -backend-config="encrypt=true"
terraform -chdir=infrastructure/terraform/stages/01-network plan -var-file=../../environments/dev/terraform.tfvars
```

It creates the VPC, public/private subnets, route tables, Internet Gateway,
single dev NAT Gateway, and EIP. Verify with `aws ec2 describe-vpcs` and
`describe-subnets`. The NAT Gateway and EIP introduce continuous cost.

The existing root remains the authoritative complete composition while stages
2–7 are migrated; do not use repeated `-target` applies as a deployment model.

Stage 03 owns EKS, the EKS encryption key, workload IAM roles, and Pod Identity
associations. Its IAM policies use the exact per-service secret mapping from
the original root. Stage 04 owns RDS, Valkey, RabbitMQ, and their consumer KMS
keys. Stage 05 owns application secret containers and CloudWatch logging.
Stage 06 reads `cluster_name` from Stage 03 remote state and owns optional
load-balancer-controller IAM plus ACM/Route53 resources. KMS remains owned by
the EKS/RDS/Valkey consuming modules rather than Stage 02.

Remote-state dependencies:

```text
03-platform  <- 01-network
04-data      <- 01-network, 03-platform
06-ingress   <- 03-platform
```

Use the shared bucket `roundready-terraform-state-jagadish` with state keys
`dev/01-network/terraform.tfstate` through `dev/06-ingress/terraform.tfstate`.
