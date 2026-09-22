# Terraform modules

The unified DEV root composes modules directly:

- `vpc` owns the VPC, six subnets, gateways, route tables, and routes.
- `k3s` owns the private K3s server/worker EC2 instances, IAM, bootstrap token,
  and node security group.
- `ecr` owns the nine private RoundReady repositories and lifecycle policies.
- `rds`, `redis`, and `rabbitmq` own private data services and their
  K3s-sourced security-group rules.
- `secrets` and `observability` own empty application secret containers and
  CloudWatch logging resources.
- `k3s-alb` owns the public ALB, listener, target group, attachments, and
  ALB-to-K3s security-group relationship.

`eks`, the historical `alb` controller module, `iam`, and `dns` remain in the
repository for reference but are not instantiated by the unified DEV root.
