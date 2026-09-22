# Terraform environment inputs

`dev/terraform.tfvars` configures the authoritative unified DEV root in the
parent `infrastructure/terraform/` directory. That root owns the complete DEV
infrastructure and uses its own S3 state key (`dev/unified/terraform.tfstate`).

The staging and production example files are retained as planning references;
this K3s conversion currently defines and validates the DEV configuration only.
Do not use those examples to deploy until their sizing, key-pair, and operational
requirements are reviewed for those environments.
