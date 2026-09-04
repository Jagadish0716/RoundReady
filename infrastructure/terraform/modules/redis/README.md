# ElastiCache Redis module

Creates one private, non-sharded ElastiCache Valkey/Redis-compatible replication group per
environment. TLS is required, data is encrypted at rest with a rotating KMS key, and an AUTH token
is generated and stored in Secrets Manager. The same version contains application-ready
`rediss://` URLs for gateway database 0 and booking database 2. Terraform outputs the endpoint and
secret ARN but never the token or credential-bearing URLs. These derived URLs add no credential
beyond the token already held in sensitive Terraform state.

The security group accepts port 6379 only from the EKS application security group. Production
requires Multi-AZ and at least one replica; development can use a single small node. Redis supports
booking locks and bounded coordination but is never the system of record—PostgreSQL remains
authoritative. Snapshot retention is deliberately modest.

Node count/type, Multi-AZ replicas, snapshots, and cross-AZ transfer are the main costs. Managed
ElastiCache avoids running failover, patching, and cache lifecycle inside EKS.
