# Stage 07 — Kubernetes workloads

This stage intentionally has no Terraform resources. Kubernetes and Kustomize
remain the deployment owner for namespaces, service accounts, Secrets Store
CSI, SecretProviderClasses, deployments, services, workers, migration Jobs,
network policies, and ingress.

After stages 01–06 are applied, build immutable images, substitute their ECR
digests in the appropriate overlay, and deploy with `kubectl apply -k` using
the existing environment overlay. Verify with `kubectl get pods,svc,ingress -n
roundready` and inspect migration Jobs before enabling public traffic.
