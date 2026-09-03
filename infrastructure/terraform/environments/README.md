# Environment states

`dev`, `staging`, and `production` use the shared foundation in the parent Terraform root and
must each use an independent S3 state key. Copy the matching `terraform.tfvars.example` to a
local, ignored `.tfvars` file and set production's region explicitly.

The environment directories intentionally contain inputs only at this stage; AWS resources are
not provisioned by this foundation. Future environment roots may call the reviewed modules
once their sizing and security interfaces are approved.

Example initialization (the bucket is bootstrapped separately; native S3 lockfiles are enabled
by the shared backend configuration):

```bash
terraform -chdir=infrastructure/terraform init \
  -backend-config="bucket=$TF_STATE_BUCKET" \
  -backend-config="key=roundready/production/terraform.tfstate" \
  -backend-config="region=$AWS_REGION" \
  -backend-config="encrypt=true"
```