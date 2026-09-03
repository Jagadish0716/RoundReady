# ElastiCache Redis module

Creates one private, non-sharded ElastiCache Valkey/Redis-compatible replication group per
environment. TLS is required, data is encrypted at rest with a rotating KMS key, and an AUTH token
is generated and stored in Secrets Manager. Terraform outputs the endpoint and secret ARN but
never the token. Applications must build authenticated `rediss://` URLs at runtime.

The security group accepts port 6379 only from the EKS application security group. Production
requires Multi-AZ and at least one replica; development can use a single small node. Redis supports
booking locks and bounded coordination but is never the system of record—PostgreSQL remains
authoritative. Snapshot retention is deliberately modest.

Node count/type, Multi-AZ replicas, snapshots, and cross-AZ transfer are the main costs. Managed
ElastiCache avoids running failover, patching, and cache lifecycle inside EKS.
