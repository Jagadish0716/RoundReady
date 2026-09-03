# Secrets Manager module

Creates environment-qualified secret containers without secret versions or placeholder values.
Operators and controlled bootstrap automation populate them later; workloads must never interpret
an empty or fake value as valid configuration. AWS-managed Secrets Manager encryption is used so
service IAM roles need only `DescribeSecret` and `GetSecretValue` on exact ARNs.

Containers cover one service database credential each, split JWT signing and verification material,
internal trust boundaries, and provider-owned Razorpay, LiveKit, Resend, and Meta WhatsApp bundles.
The RDS master secret is separate and is never granted to application workloads.
