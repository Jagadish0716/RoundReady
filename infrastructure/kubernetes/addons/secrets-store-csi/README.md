# Secrets Store CSI runtime delivery

RoundReady uses one secret-delivery path:

```text
AWS Secrets Manager -> EKS Pod Identity -> AWS CSI provider
  -> mounted files -> synchronized service-owned Kubernetes Secret
  -> application environment variables
```

The applications currently consume environment variables rather than files.
Consequently, CSI secret synchronization is enabled. Values originate only from
Secrets Manager; no Kubernetes Secret values are committed. The CSI mount is
required for synchronization and is attached to every HTTP/worker Deployment of
the owning service. The frontend has neither a mount nor AWS secret permissions.

Synchronized Secrets are stored in etcd and remain visible to namespace users
with Secret read permission. Enable EKS envelope encryption, restrict Kubernetes
RBAC, audit Secret access, and remember that removing all consuming pods also
removes the synchronized Secret. Rotation refreshes the Kubernetes Secret, but
environment variables update only after pods restart; coordinate rollouts after
credential rotation.

## Add-ons

Pin and install in `kube-system`:

- Secrets Store CSI Driver chart/application `1.6.0`
- AWS provider chart/image `3.1.3`

The driver values enable Secret synchronization, rotation polling, and the token
audiences used by AWS/EKS Pod Identity. The provider does not install a second
driver. Neither add-on contains application credentials.

```bash
helm repo add secrets-store-csi-driver \
  https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm repo add aws-secrets-manager \
  https://aws.github.io/secrets-store-csi-driver-provider-aws
helm repo update

helm upgrade --install csi-secrets-store \
  secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system \
  --version 1.6.0 \
  --values infrastructure/kubernetes/addons/secrets-store-csi/driver-values.yaml \
  --wait

helm upgrade --install secrets-provider-aws \
  aws-secrets-manager/secrets-store-csi-driver-provider-aws \
  --namespace kube-system \
  --version 3.1.3 \
  --values infrastructure/kubernetes/addons/secrets-store-csi/aws-provider-values.yaml \
  --wait
```

Do not execute these commands until the EKS Pod Identity Agent is healthy.

## Secret JSON contract

Terraform creates environment-qualified containers; operators/bootstrap populate
JSON values. The SecretProviderClasses extract only these owned keys:

- database containers: `database_url` containing the owning service's
  `postgresql+asyncpg://` URL;
- `jwt-signing` / `jwt-verification`: `jwt_signing_key` /
  `jwt_verification_key`;
- `internal-identity`: `internal_identity_secret` and
  `notification_internal_identity_secret`; `internal-service`:
  `internal_service_secret`;
- `razorpay`: `key_id`, `key_secret`, `webhook_secret`;
- `livekit`: `api_key`, `api_secret`;
- `resend`: `api_key`; `meta-whatsapp`: `access_token`, `phone_number_id`;
- Redis credentials: application-ready `redis_url` and `booking_redis_url` using
  `rediss://`; RabbitMQ credentials: application-ready `rabbitmq_url` using
  `amqps://`.

Terraform stores these application-ready TLS URLs in the existing managed secret
versions after the ElastiCache/Amazon MQ endpoints exist. The derived URLs are
never output and introduce no additional credential beyond values already held in
sensitive Terraform state. Manifests do not assemble credentials in ConfigMaps or
shell code. User-service has no RabbitMQ behavior, so its stale RabbitMQ setting
and production validation were removed rather than broadening IAM.

The current Kustomize secret-name substitution uses legacy `vars`. It remains
functional but emits a deprecation warning; migration to structured replacements
is deferred because the CSI provider represents its object list as one multiline
scalar and a small safe replacement is not available.

## Deployment order

1. Apply Terraform for the target environment.
2. Verify the EKS Pod Identity Agent and associations.
3. Install the CSI driver and AWS provider.
4. Populate provider/internal Secrets Manager containers.
5. Run controlled DB bootstrap to populate service database URLs.
6. Deploy SecretProviderClasses and workloads.

Validate mounts, synchronized Secret ownership, TLS URL schemes, and rotation in
a non-production cluster before rollout. Never print secret contents during
verification.
