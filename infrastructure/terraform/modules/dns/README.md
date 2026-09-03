# Route 53 and ACM prerequisites

This module uses an existing public Route 53 hosted zone by ID or name; it never registers a domain
or creates/deletes the parent hosted zone. When enabled, it requests one regional ACM certificate
for the configured frontend and API hostnames, creates DNS validation records, and waits for DNS
validation. Certificate material is never output.

Application alias records are intentionally deferred because the ALB does not exist until a future
Kubernetes Ingress is reconciled by AWS Load Balancer Controller. After that ALB hostname and zone
ID exist, deployment automation can create aliases without fabricating a target or splitting ALB
ownership between Terraform and Kubernetes.
