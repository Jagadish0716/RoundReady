# AWS deployment order

`infrastructure/terraform/` is the single authoritative RoundReady DEV
Terraform root. It creates the VPC, single NAT Gateway, nine ECR repositories,
two private K3s nodes, private managed data services, application secret
containers, CloudWatch application logging, and the Terraform-managed HTTP ALB.
The numbered stage roots under `infrastructure/terraform/stages/` are historical
references and must not be applied alongside the unified root.

1. Configure AWS credentials for the intended account and `ap-south-1`.
2. Initialize the unified root with the S3 backend documented in
   `infrastructure/terraform/README.md`.
3. Run formatting, `terraform validate`, and a saved full DEV plan. Review the
   resource actions, costs, and teardown settings before a separately approved
   apply.
4. Verify the VPC and routes, private K3s server/worker, SSM access, private
   RDS/Valkey/RabbitMQ, ECR repositories, secret containers, CloudWatch log
   group, and ALB target configuration.
5. Use Systems Manager Session Manager for node administration. The K3s join
   token is stored as a Terraform-owned SSM SecureString; its value is present
   in protected Terraform state and is not an output.
6. Populate application secret values through the approved secret-management
   process. Terraform creates their containers only. Database service
   credential values remain managed by their respective Terraform modules.
7. Build, scan, and push immutable ARM64-compatible service images to ECR.
   Terraform does not build or push images.
8. Run controlled database bootstrap and migrations from the private network.
   Stop if any migration job fails.
9. Deploy Kubernetes workloads separately. The frontend Service is a NodePort
   on 30080; the public ALB forwards HTTP traffic to both private K3s nodes.
10. Verify frontend readiness, ALB target health, data-service connectivity,
    and application behavior. Keep the Terraform state, saved plan, and
    generated infrastructure credentials protected.

K3s uses two `t4g.small` ARM64 nodes and is a cost-optimized, non-HA DEV
topology. Free Tier eligibility is not asserted. RDS and Valkey use
customer-managed KMS keys whose deletion is scheduled for AWS's configured
30-day waiting period when Terraform destroys them. A complete DEV teardown is
performed through the same unified root after reviewing the destroy plan.
