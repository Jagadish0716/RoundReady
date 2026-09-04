# AWS deployment order

This is the authoritative dependency order for a RoundReady environment. Deploy
`dev` first; never reuse its state, secrets, images, or runtime values for
staging or production.

1. Configure operator AWS credentials, region, encrypted remote-state backend,
   environment-specific state key, and reviewed environment variables.
2. Run `terraform init`, formatting/validation, and `terraform plan`.
3. Review the plan, service quotas, and estimated EKS, NAT, RDS, ElastiCache,
   Amazon MQ, ALB, and CloudWatch costs.
4. Apply Terraform for **dev only** and verify VPC, private EKS nodes, private
   managed data services, ECR, ACM, Secrets Manager, and Pod Identity resources.
5. Configure `kubectl` for that cluster and verify operator access.
6. Verify or install the EKS Pod Identity Agent.
7. Install the pinned Secrets Store CSI Driver and AWS provider in `kube-system`.
8. Populate environment-specific provider/internal runtime secret containers.
9. Run the controlled database bootstrap from an approved private-network path;
   verify seven service database secrets and no application access to the RDS
   master secret.
10. Build, scan, and push immutable backend/service images to that environment's
    ECR repositories. Workers reuse the owning service image.
11. Build the frontend with
    `NEXT_PUBLIC_API_BASE_URL=https://<environment-api-host>`, then scan and push
    its immutable image.
12. Replace every image marker with a reviewed tag/digest and run the seven
    service-specific Alembic migration Jobs. Stop if any Job fails.
13. Deploy backend APIs, workers, API gateway, and frontend; verify readiness and
    internal dependency connectivity.
14. Install the pinned AWS Load Balancer Controller in `kube-system` using its
    Terraform-created Pod Identity association.
15. Resolve the production Ingress inputs from the same environment, pass the
    fail-closed ingress validation, and deploy the shared frontend/API Ingress.
16. Obtain the controller-created ALB DNS name and canonical hosted-zone ID.
17. Set both deferred Terraform ALB alias inputs, review the plan, and apply only
    the Route 53 alias change.
18. Verify DNS, certificate, HTTP-to-HTTPS redirect, host routing, target health,
    CORS, and the frontend's build-time API URL.
19. Run the existing end-to-end application validation against that environment.
20. Record release, image digests, migration revisions, validation evidence, and
    rollback checkpoints before promoting the same process to staging/production.

The ordering resolves the intentional cycles: Terraform creates ACM/hostnames
before the frontend build and Ingress; images exist before migration Jobs;
secrets and databases exist before migrations/workloads; the controller creates
the ALB before Terraform creates DNS aliases. Observability deployment is
intentionally deferred and does not block this sequence.

No step authorizes `terraform apply` or `kubectl apply` without a reviewed plan,
explicit environment selection, populated runtime inputs, and operator approval.
