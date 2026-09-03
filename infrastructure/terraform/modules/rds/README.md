# RDS PostgreSQL module

Creates one private Amazon RDS PostgreSQL instance per environment. It uses only the VPC's private
data subnets, accepts TCP 5432 only from the configured EKS application security group, encrypts
storage with a rotating customer-managed KMS key, and lets RDS manage the master password in
Secrets Manager. Terraform exposes the secret ARN but never reads or outputs its value.

The instance hosts seven logical service-owned databases: `roundready_auth`, `roundready_user`,
`roundready_interviewer`, `roundready_booking`, `roundready_payment`, `roundready_interview`, and
`roundready_notification`. Terraform intentionally does not create those databases or their roles.
After RDS is ready, a controlled bootstrap process retrieves the master credential, creates one
login/owner per database, revokes cross-database access, stores each application credential through
runtime secret injection, and stops using the master account for application traffic.

Production-mode validation requires Multi-AZ, deletion protection, a final snapshot, and at least
seven days of automated backups. Enhanced Monitoring and PostgreSQL CloudWatch log export are
configurable. The current EKS cluster security group is the narrow workload source boundary;
pod-level security groups can replace it later without widening database ingress.
