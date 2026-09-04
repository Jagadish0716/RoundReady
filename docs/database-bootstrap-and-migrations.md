# Production database bootstrap and migrations

RoundReady uses one private RDS PostgreSQL instance per environment and seven
logically isolated databases and owner roles. Application workloads never use
the RDS master credential. Bootstrap is an explicit operator action from a
controlled host or one-shot runner inside the private VPC path allowed to reach
RDS; do not make RDS public or widen its security group.

## Bootstrap

Prerequisites are AWS CLI credentials for the intended account, `psql`, and
access to the RDS master secret plus the seven existing Terraform-created
service database secret containers. Use immutable/operator-audited tooling and
do not enable shell tracing.

Export the non-secret Terraform ARN map to a protected temporary location, then
validate the requested target without network or mutations:

```bash
terraform -chdir=infrastructure/terraform output -json application_secret_arns > /secure/tmp/database-secret-arns.json
python scripts/bootstrap-production-databases.py \
  --environment production \
  --region ap-south-1 \
  --expected-account-id 123456789012 \
  --rds-endpoint roundready-production.example.ap-south-1.rds.amazonaws.com \
  --master-secret-id <rds-master-secret-arn> \
  --service-secret-map /secure/tmp/database-secret-arns.json
```

After review, repeat with `--execute --confirm production`. Execution checks the
active AWS account, selected RDS endpoint, master secret, and all seven target
secret containers. It creates missing roles/databases, reconciles ownership,
revokes public/cross-service access, reuses existing valid passwords on rerun,
and writes only `{"database_url":"postgresql+asyncpg://..."}` to each owning
service secret. New passwords use cryptographically secure randomness. Secret
values are never printed, placed in Terraform outputs, Git, command arguments,
or temporary files. A failure exits non-zero; fix it and rerun rather than
dropping databases or roles.

The master secret is used only by this controlled bootstrap process. It is not
mounted into application or migration pods. The resulting ownership is:

| Service | Database / role | Runtime secret key |
| --- | --- | --- |
| auth-service | `roundready_auth` | `auth_database` |
| user-service | `roundready_user` | `user_database` |
| interviewer-service | `roundready_interviewer` | `interviewer_database` |
| booking-service | `roundready_booking` | `booking_database` |
| payment-service | `roundready_payment` | `payment_database` |
| interview-service | `roundready_interview` | `interview_database` |
| notification-service | `roundready_notification` | `notification_database` |

## Migration Jobs

`infrastructure/kubernetes/migrations` renders exactly seven independent Jobs.
Each uses the existing immutable service image, service account/Pod Identity,
and a migration-only SecretProviderClass that resolves only its database URL.
No Job receives the master credential, Redis, RabbitMQ, or provider secrets.
Jobs run `alembic -c alembic.ini upgrade head`, use `restartPolicy: Never`, have
bounded retry/runtime/resources, and expose no port or Service.

For the selected environment, replace every image marker with the same verified
image digest intended for the application release. Render and review before
applying:

```bash
kustomize build infrastructure/kubernetes/migrations/overlays/production
kubectl apply -k infrastructure/kubernetes/migrations/overlays/production
kubectl get jobs -n roundready -l app.kubernetes.io/component=migration
kubectl logs -n roundready job/auth-service-migration
```

Delete completed Jobs deliberately before rerunning a migration release; never
automate downgrades. A failed Job blocks deployment and requires investigation.

## Required deployment order

Follow the authoritative sequence in `docs/aws-deployment-runbook.md`. In
particular, build and push immutable service images after bootstrap and before
running the seven migration Jobs. Deploy application workloads only after every
Job succeeds.

Production application Deployments start their application/worker commands
directly and never run Alembic. Local Docker Compose may retain its explicitly
development-only migration-on-start convenience.
