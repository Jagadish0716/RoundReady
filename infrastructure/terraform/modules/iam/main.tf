locals {
  service_accounts = { for service in keys(var.service_secret_arns) : service => service }
}

data "aws_iam_policy_document" "pod_identity_trust" {
  for_each = var.service_secret_arns

  statement {
    sid     = "AllowEksAuthToAssumeRoleForPodIdentity"
    effect  = "Allow"
    actions = ["sts:AssumeRole", "sts:TagSession"]

    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/eks-cluster-arn"
      values   = [var.cluster_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/kubernetes-namespace"
      values   = [var.namespace]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/kubernetes-service-account"
      values   = [local.service_accounts[each.key]]
    }
  }
}

resource "aws_iam_role" "service" {
  for_each = var.service_secret_arns

  name               = "${var.name_prefix}-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.pod_identity_trust[each.key].json

  tags = merge(var.common_tags, {
    Name           = "${var.name_prefix}-${each.key}"
    ServiceAccount = local.service_accounts[each.key]
  })
}

data "aws_iam_policy_document" "secret_access" {
  for_each = var.service_secret_arns

  statement {
    sid       = "ReadOwnedSecrets"
    effect    = "Allow"
    actions   = ["secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue"]
    resources = each.value
  }
}

resource "aws_iam_role_policy" "secret_access" {
  for_each = var.service_secret_arns

  name   = "owned-secret-read"
  role   = aws_iam_role.service[each.key].id
  policy = data.aws_iam_policy_document.secret_access[each.key].json
}

resource "aws_eks_pod_identity_association" "service" {
  for_each = var.create_pod_identity_associations ? var.service_secret_arns : {}

  cluster_name    = var.cluster_name
  namespace       = var.namespace
  service_account = local.service_accounts[each.key]
  role_arn        = aws_iam_role.service[each.key].arn

  tags = merge(var.common_tags, { Service = each.key })
}
