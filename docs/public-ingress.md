# Public ALB ingress and DNS handoff

Production uses one internet-facing Application Load Balancer for two host-based
routes. AWS Load Balancer Controller owns the ALB; Terraform does not create an
`aws_lb` resource.

```text
https://<frontend-host> -> frontend ClusterIP:3000
https://<api-host>      -> api-gateway ClusterIP:8000 -> private services
```

The Ingress selects class `alb`, IP targets, tagged public ELB subnets, HTTPS
443, and an HTTP 80 redirect to HTTPS. It uses the pinned modern
`ELBSecurityPolicy-TLS13-1-2-2021-06`. The ACM certificate covers both distinct
hosts. Frontend health uses `/`; gateway health uses `/ready`; both require
HTTP 200. No backend microservice or worker has a public route, NodePort, or
LoadBalancer Service.

## Required production inputs

Before deployment, replace all four `REQUIRED_*` values in
`infrastructure/kubernetes/overlays/production/public-ingress-config.yaml` from
the selected environment's Terraform outputs/configuration:

- `FRONTEND_HOST` from `frontend_hostname`
- `API_HOST` from `api_hostname`
- `ACM_CERTIFICATE_ARN` from `public_certificate_arn`
- `VPC_CIDR` from `vpc_cidr`

Render and run the mandatory fail-closed gate:

```bash
kustomize build infrastructure/kubernetes/overlays/production > /secure/tmp/roundready-production.yaml
python scripts/validate-kubernetes-public-ingress.py /secure/tmp/roundready-production.yaml
```

The validator rejects unresolved markers, invalid/duplicate hosts, a malformed
certificate ARN, non-private source CIDR, missing HTTPS/IP/security-group
settings, any public backend target, and any non-ClusterIP application Service.
Do not apply a render that fails this gate. Dev and staging omit public Ingress
entirely.

Build the frontend image before push/deployment with the same API hostname:

```bash
docker build --build-arg NEXT_PUBLIC_API_BASE_URL=https://<api-host> -f frontend/Dockerfile .
```

This value is public and build-time; changing the running pod environment does
not modify the browser bundle.

## Security and NetworkPolicy

The controller creates the frontend ALB security group and, through
`manage-backend-security-group-rules`, manages the narrow backend rule required
for IP targets. No security-group ID or AWS account ID is committed. EKS nodes
remain private.

Kubernetes NetworkPolicy cannot select an AWS ALB security group. The production
policies therefore permit only private VPC-CIDR sources, frontend pods on 3000,
and api-gateway pods on 8000. They never select backend pods. The
controller-managed security-group rule is the authoritative ALB-only source
restriction; the NetworkPolicy is a second layer scoped to entrypoint pods and
ports. Revalidate source-IP behavior with the deployed VPC CNI before traffic
cutover.

## Route 53 handoff

After applying the Ingress, obtain its real ALB hostname from status. Resolve the
ALB canonical hosted-zone ID through the AWS ELBv2 API, then set both Terraform
inputs `public_alb_dns_name` and `public_alb_zone_id`. A subsequent Terraform
plan/apply creates frontend and API alias A records in the existing public zone.
Both values are optional before the ALB exists and must be supplied together;
the DNS module never guesses them. Verify records and HTTPS before cutover.
