# Historical staged Terraform implementations

The numbered roots in this directory document the earlier staged deployment
approach. They are not required for RoundReady DEV deployment and do not share
the authoritative unified state.

Use [`../README.md`](../README.md) and the single root at
`infrastructure/terraform/` for DEV plan/apply/destroy operations. Do not apply
these stage roots alongside the unified root: that would create duplicate
Terraform ownership for the same environment resources.

The stage roots retain `terraform_remote_state` references for historical
reference only. The unified root uses direct module outputs and inputs.
