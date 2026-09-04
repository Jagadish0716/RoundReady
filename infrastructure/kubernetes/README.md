# RoundReady Kubernetes foundation

This directory defines the Kubernetes-side foundation and internal application
workloads for RoundReady on EKS. It deliberately creates no public Ingress,
database-bootstrap Job, or observability component. Explicit database migration
Jobs live separately under `migrations/`.

Use `docs/aws-deployment-runbook.md` as the authoritative deployment order.

## Layout and ownership

- `base/` contains the namespace, ServiceAccounts, non-secret configuration,
  frontend/backend HTTP and worker Deployments, internal Services, and ingress
  policies.
- `overlays/dev`, `overlays/staging`, and `overlays/production` customize the
  environment without copying complete workloads. Production adds replicas,
  topology spreading, and disruption budgets.
- Terraform owns AWS resources and EKS Pod Identity associations. Kubernetes
  manifests own the namespace, ServiceAccounts, Deployments, Services,
  ConfigMaps, probes, policies, and future Ingress. ServiceAccount names and the
  `roundready` namespace match the Terraform IAM interfaces.

No IRSA annotations or static AWS credentials belong on these ServiceAccounts.
EKS Pod Identity requires its agent on the cluster and an AWS-side association;
the Kubernetes ServiceAccount itself contains no role ARN. Token projection is
enabled because every current backend identity, including the gateway, has
least-privilege Secrets Manager access through the existing Terraform mapping.
The frontend has a dedicated ServiceAccount with token automount disabled and no
Pod Identity or IAM permissions because it does not call AWS APIs.

## Configuration and secrets

`roundready-runtime-config` contains only the runtime environment, log level,
and telemetry switch. Service DNS URLs and non-secret production provider-mode
selectors are explicit on the workloads that require them. Staging uses
production application safeguards; the dev overlay selects development runtime
and providers. Do not place passwords, JWT material, provider credentials,
database URLs containing credentials, or other secrets in ConfigMaps.

Secrets are resolved from AWS Secrets Manager through each service's
least-privilege EKS Pod Identity and the AWS Secrets Store CSI provider. Because
applications require environment variables, the driver dynamically synchronizes
service-owned Kubernetes Secrets; no values exist in Git. See
`addons/secrets-store-csi/README.md` for lifecycle and installation requirements.
Controlled bootstrap/migration execution is documented in
`docs/database-bootstrap-and-migrations.md`. Do not add plaintext Secret
manifests, secret generators, or credentials baked into images.
Terraform state is not an application secret-delivery mechanism.

## Network topology

The intended request path is:

```text
Internet (future) -> ALB (future) -+-> frontend
                                   +-> api-gateway -> backend ClusterIP services
                                                     -> AWS managed dependencies
```

Only future public entry points may be exposed through an ingress/load balancer.
All current Services, including frontend and gateway, are `ClusterIP`, so neither
is publicly reachable. Browser API traffic must use the gateway hostname and
never address an individual microservice.
Internal service-to-service REST calls remain private. RDS, ElastiCache, Amazon
MQ, Secrets Manager, and external provider traffic leaves through the VPC paths
defined by Terraform.

The base applies namespace-wide default-deny ingress and explicit allowances
only for gateway-to-backend HTTP and notification-worker-to-user-service
recipient resolution. Workers accept no inbound traffic. Frontend and gateway
remain isolated until the public-routing phase. Egress stays unrestricted so
DNS, AWS APIs, managed data stores, Amazon MQ, and providers remain reachable.
Strict egress is deferred until exact endpoints and CNI behavior are known.

Kubelet HTTP-probe source handling differs by EKS VPC CNI policy-enforcement
mode. Confirm `/health` and `/ready` probe traffic in the target cluster before
rollout and add the narrow cluster-specific allowance if needed; a broad source
CIDR is intentionally not guessed here.

## Backend workloads

Every workload uses the standard labels:
`app.kubernetes.io/name`, `app.kubernetes.io/component`,
`app.kubernetes.io/part-of=roundready`, and
`app.kubernetes.io/managed-by=kustomize`.

The eight HTTP Deployments preserve the image's one-Uvicorn-process command and
listen on `8000`. Separate Deployments run only the existing worker entrypoints:
auth/interviewer/payment/interview outbox publishers, booking maintenance and
payment-event consumers, the interview booking-event consumer, and the
notification consumer. Workers reuse service images and have no Service or fake
HTTP probe.

All pods run non-root with RuntimeDefault seccomp; containers prohibit privilege
escalation, drop all capabilities, and use a read-only root filesystem with a
bounded writable `/tmp`. HTTP containers expose startup `/health`, readiness
`/ready`, and liveness `/health` probes. HTTP termination grace is 30 seconds;
workers receive 60 seconds for consumer shutdown and in-flight handling.

Initial HTTP resources are `100m/128Mi` requests and `500m/512Mi` limits; workers
use `50m/96Mi` and `250m/256Mi`. These conservative baselines must be tuned from
measurements. HPA and node autoscaling integration are deferred until real load
data exists.

Dev and staging use one replica. Production uses two replicas for every HTTP
component, zero-unavailable rolling updates, per-service disruption budgets, and
best-effort zone/hostname topology spreading scoped to each application. Workers
remain at one replica to preserve conservative consumer concurrency. Increase
them only after validating queue semantics and throughput.

Images use explicit replacement markers and never `latest`. Deployment tooling
must replace each `roundready/<component>:replace-with-immutable-id` with its ECR
repository and a verified Git/release tag, preferably an image digest such as
`<repository-uri>@sha256:<verified-digest>`. Account IDs are not stored here.

No PostgreSQL, Redis/Valkey, or RabbitMQ workload is deployed. Runtime wiring will
target RDS, ElastiCache, and Amazon MQ without embedding endpoints or credentials.

## Frontend workload

The frontend preserves the standalone production command (`node server.js`) and
port `3000`; it never starts development tooling. It uses a restricted security
context and bounded writable volumes for `/tmp` and `/app/.next/cache` while the
root filesystem remains read-only. Because there is no dedicated frontend health
endpoint, startup/readiness/liveness probes use the existing lightweight `/`
route. Production has two replicas, zero-unavailable rolling updates, a PDB, and
per-application zone/hostname spreading; dev and staging use one replica.

`NEXT_PUBLIC_API_BASE_URL` is a public **build-time** value. The Docker builder
passes it into `next build`, which embeds it in browser assets and validates that
production uses a non-local HTTPS gateway URL. Setting it on a running pod cannot
change an already-built bundle. Build or promote an image with the correct target
gateway URL:

```bash
docker build --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.example.com \
  -f frontend/Dockerfile .
```

Do not inject backend DNS names, AWS credentials, internal identity material, or
provider secrets into the frontend. Browser requests use the gateway URL embedded
in the image and do not call backend Services directly.

## Validation

Render every overlay without contacting a cluster:

```bash
kustomize build infrastructure/kubernetes/overlays/dev
kustomize build infrastructure/kubernetes/overlays/staging
kustomize build infrastructure/kubernetes/overlays/production
```

Before deployment, replace all image markers and validate runtime secret/config
wiring. `kubectl kustomize` may be used when standalone Kustomize is unavailable.
Do not apply these manifests until runtime secrets have been populated,
migrations have succeeded, immutable images are selected, and probe behavior
has been validated for the target EKS networking mode.

Render migration Jobs independently; they are intentionally excluded from the
application overlays so deployment replicas cannot race schema changes:

```bash
kustomize build infrastructure/kubernetes/migrations/overlays/dev
kustomize build infrastructure/kubernetes/migrations/overlays/staging
kustomize build infrastructure/kubernetes/migrations/overlays/production
```
