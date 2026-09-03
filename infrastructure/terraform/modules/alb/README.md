# AWS Load Balancer Controller prerequisites

This module deliberately creates no ALB, listener, or target group. A future Kubernetes Ingress
will make the AWS Load Balancer Controller the single owner of those resources. Terraform creates
its Pod Identity-compatible IAM role, Pod Identity association for
`kube-system/aws-load-balancer-controller`, and the AWS-recommended policy pinned to controller
`v2.14.1`. The policy source is the versioned upstream installation policy referenced by the AWS
EKS installation guide.

Installing the controller, Pod Identity Agent, ServiceAccount, Ingress, and Services is deferred.
The future public ALB uses public subnets and accepts 443; optional port
80 only redirects to HTTPS. Backend ports and EKS nodes receive no public ingress. Use a modern AWS
TLS listener policy, the ACM certificate ARN from the DNS module, and `/ready` for target routing so
pods receive traffic only when required dependencies are available.
