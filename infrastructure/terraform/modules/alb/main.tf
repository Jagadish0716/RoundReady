resource "aws_iam_policy" "controller" {
  count       = var.enabled ? 1 : 0
  name        = "${var.name_prefix}-aws-load-balancer-controller"
  description = "Pinned AWS Load Balancer Controller ${var.controller_version} permissions"
  policy      = file("${path.module}/iam_policy_v2.14.1.json")

  tags = var.common_tags
}

resource "aws_iam_role" "controller" {
  count = var.enabled ? 1 : 0
  name  = "${var.name_prefix}-aws-load-balancer-controller"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowEksAuthToAssumeRoleForPodIdentity"
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "controller" {
  count      = var.enabled ? 1 : 0
  role       = aws_iam_role.controller[0].name
  policy_arn = aws_iam_policy.controller[0].arn
}

resource "aws_eks_pod_identity_association" "controller" {
  count = var.enabled ? 1 : 0

  cluster_name    = var.cluster_name
  namespace       = "kube-system"
  service_account = "aws-load-balancer-controller"
  role_arn        = aws_iam_role.controller[0].arn

  depends_on = [aws_iam_role_policy_attachment.controller]
}
