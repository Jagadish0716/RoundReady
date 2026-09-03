# AWS Load Balancer Controller

RoundReady installs AWS Load Balancer Controller with the official AWS EKS Helm
chart. Chart `1.14.1` is pinned to controller `v2.14.1`, matching the committed
Terraform IAM policy. The release belongs in `kube-system`; application manifests
remain Kustomize-managed in `roundready`.

## Identity and ownership

Helm creates the dedicated `aws-load-balancer-controller` ServiceAccount without
IRSA annotations or static AWS credentials. Terraform creates the least-privilege
controller role/policy and its EKS Pod Identity association for exactly:

```text
kube-system/aws-load-balancer-controller
```

The EKS Pod Identity Agent must already be operational. The ServiceAccount name,
namespace, and Terraform association must not be changed independently.

## Values

`values.common.yaml` contains non-secret settings shared by every environment.
Environment files set only replicas and disruption behavior. Cluster name, AWS
region, and VPC ID are mandatory installation inputs sourced from Terraform
outputs; they are intentionally not represented by fake placeholders or
hardcoded account/environment values.

The controller uses `ip` targets, compatible with the existing Amazon VPC CNI.
Future ALBs will target frontend and API-gateway pods in private application
subnets without NodePort. Public ALBs discover only public subnets tagged
`kubernetes.io/role/elb=1`; EKS nodes remain private.

## Manual installation

Run only after Terraform has created the cluster, controller IAM resources, Pod
Identity association, and the EKS Pod Identity Agent is ready:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update

CLUSTER_NAME="$(terraform -chdir=infrastructure/terraform output -raw eks_cluster_name)"
AWS_REGION="$(terraform -chdir=infrastructure/terraform output -raw aws_region)"
VPC_ID="$(terraform -chdir=infrastructure/terraform output -raw vpc_id)"

helm upgrade --install aws-load-balancer-controller \
  eks/aws-load-balancer-controller \
  --namespace kube-system \
  --version 1.14.1 \
  --values infrastructure/kubernetes/addons/aws-load-balancer-controller/values.common.yaml \
  --values infrastructure/kubernetes/addons/aws-load-balancer-controller/values.production.yaml \
  --set-string clusterName="${CLUSTER_NAME}" \
  --set-string region="${AWS_REGION}" \
  --set-string vpcId="${VPC_ID}" \
  --wait
```

Select `values.dev.yaml` or `values.staging.yaml` for those environments. Never
reuse Terraform outputs across environments.

Verify after installation:

```bash
kubectl get deployment -n kube-system aws-load-balancer-controller
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
kubectl logs -n kube-system deployment/aws-load-balancer-controller
```

## Deferred ingress boundary

No Ingress or ALB is created here. A later shared Ingress will produce:

```text
Internet -> public ALB -> frontend/api-gateway ClusterIP Services
```

It will reference the environment ACM certificate ARN, enforce HTTPS, select
public ELB-tagged subnets, and use `ip` targets. Backend services remain private.
14I.9g must add narrow ALB-to-frontend/API-gateway NetworkPolicy allowances based
on the final controller target/security-group model; the current RoundReady
default-deny policy is intentionally unchanged.

Local rendering requires explicit non-secret values:

```bash
helm template aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --version 1.14.1 \
  --values infrastructure/kubernetes/addons/aws-load-balancer-controller/values.common.yaml \
  --values infrastructure/kubernetes/addons/aws-load-balancer-controller/values.production.yaml \
  --set-string clusterName=roundready-validation \
  --set-string region=ap-south-1 \
  --set-string vpcId=vpc-validation
```
