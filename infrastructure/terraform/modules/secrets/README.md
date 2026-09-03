# Secrets Manager module

Planned interface: environment-scoped secret names, KMS encryption, rotation ownership, and
least-privilege workload access. Secret values should be created outside Terraform where
possible so they do not enter Terraform state.
