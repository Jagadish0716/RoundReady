# RoundReady unified DEV Terraform root

`infrastructure/terraform/` is the authoritative unified DEV Terraform root.
It owns the VPC, one NAT Gateway, nine ECR repositories, two private K3s EC2
nodes, private RDS/Valkey/RabbitMQ, application secret containers, CloudWatch
application logging, and the public HTTP ALB. The `stages/` directories remain
historical/reference implementations and are not part of the DEV deployment
workflow.

## DEV workflow

From the repository root, initialize this root with the existing S3 backend
strategy and an independent unified state key:

```bash
terraform -chdir=infrastructure/terraform init \
  -backend-config="bucket=roundready-terraform-state-jagadish" \
  -backend-config="key=dev/unified/terraform.tfstate" \
  -backend-config="region=ap-south-1" \
  -backend-config="encrypt=true"
terraform -chdir=infrastructure/terraform validate
terraform -chdir=infrastructure/terraform plan \
  -var-file=environments/dev/terraform.tfvars \
  -out=/secure/local/path/roundready-dev.tfplan
```

Review the saved plan before any separately authorized apply. The full
configuration can be created with one apply and removed with one destroy:

```bash
terraform -chdir=infrastructure/terraform apply \
  -var-file=environments/dev/terraform.tfvars
terraform -chdir=infrastructure/terraform destroy \
  -var-file=environments/dev/terraform.tfvars
```

Kubernetes workloads remain separately deployed. Terraform creates the ALB
and registers both K3s nodes on TCP 30080; the frontend Service manifest
provides that NodePort.

## K3s join-token handling

Terraform generates a 64-character random token and owns its SSM Parameter
Store `SecureString` at `/<project>-<environment>/k3s/join-token`. The server
and worker fetch it at boot using narrowly scoped instance-role permissions.
The parameter is therefore deleted by Terraform destroy along with both
instances. The token value is **present in Terraform state** because Terraform
manages both the random value and SecureString resource; it is marked sensitive
for display but is not absent from state. Protect the S3 backend, local plan
files, and any state copies as secrets. The token is not an output or part of
user-data.

## Teardown notes

DEV ECR repositories allow force deletion of images, the RDS instance has
deletion protection disabled and skips its final snapshot, and generated
Secrets Manager credentials use a zero-day recovery window. Terraform owns the
ALB listener, target attachments, target group, security groups, EC2 instances,
and runtime SSM token parameter. RDS and Valkey use customer-managed KMS keys;
destroy schedules those keys for deletion after AWS's configured 30-day
waiting period, so their physical deletion is not immediate. Do not expect a
KMS key scheduled for deletion to disappear synchronously.

The selected DEV K3s node type is `t4g.small` (ARM64); Free Tier eligibility is
not asserted. K3s image pull IAM actions are limited to the nine RoundReady ECR
repositories, with only `ecr:GetAuthorizationToken` using `Resource = "*"` as
required by AWS. Application images are not built or pushed by this Terraform
root.

Terraform state also contains generated Valkey and RabbitMQ credential values
because their existing service modules create the credentials and corresponding
Secrets Manager versions together. The application secret containers remain
empty until their values are supplied separately.
