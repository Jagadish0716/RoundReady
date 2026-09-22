data "aws_ssm_parameter" "ubuntu_ami" {
  name = var.ami_ssm_parameter
}

data "aws_caller_identity" "current" {}

locals {
  server_ip         = cidrhost("10.10.16.0/21", 10)
  join_token_name   = "/${var.name_prefix}/k3s/join-token"
  join_token_policy = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.join_token_name}"

  server_user_data = <<-USERDATA
    #!/bin/bash
    set -Eeuo pipefail
    exec > >(tee -a /var/log/roundready-k3s-bootstrap.log) 2>&1
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y awscli curl snapd
    if ! systemctl is-active --quiet snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null && ! systemctl is-active --quiet amazon-ssm-agent 2>/dev/null; then
      snap install amazon-ssm-agent --classic || true
    fi
    systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null || systemctl enable --now amazon-ssm-agent
    TOKEN="$(aws ssm get-parameter --region ${var.aws_region} --name ${local.join_token_name} --with-decryption --query Parameter.Value --output text 2>/dev/null)"
    export K3S_TOKEN="$TOKEN"
    curl -sfL https://get.k3s.io | sh -s - server --write-kubeconfig-mode 644
    unset K3S_TOKEN TOKEN
  USERDATA

  worker_user_data = <<-USERDATA
    #!/bin/bash
    set -Eeuo pipefail
    exec > >(tee -a /var/log/roundready-k3s-bootstrap.log) 2>&1
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y awscli curl snapd
    if ! systemctl is-active --quiet snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null && ! systemctl is-active --quiet amazon-ssm-agent 2>/dev/null; then
      snap install amazon-ssm-agent --classic || true
    fi
    systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null || systemctl enable --now amazon-ssm-agent
    deadline=$$(($${SECONDS} + 900))
    TOKEN=""
    until [ "$${SECONDS}" -ge "$${deadline}" ]; do
      TOKEN="$$(aws ssm get-parameter --region ${var.aws_region} --name ${local.join_token_name} --with-decryption --query Parameter.Value --output text 2>/dev/null || true)"
      if [ -n "$${TOKEN}" ] && timeout 5 bash -c '</dev/tcp/${local.server_ip}/6443' 2>/dev/null; then
        break
      fi
      TOKEN=""
      sleep 10
    done
    if [ -z "$${TOKEN}" ]; then
      echo "Timed out waiting for K3s server token and API readiness" >&2
      exit 1
    fi
    export K3S_URL=https://${local.server_ip}:6443
    export K3S_TOKEN="$${TOKEN}"
    curl -sfL https://get.k3s.io | sh -
    unset K3S_URL K3S_TOKEN TOKEN
  USERDATA
}

resource "random_password" "join_token" {
  length  = 64
  special = false
}

resource "aws_ssm_parameter" "join_token" {
  name        = local.join_token_name
  description = "RoundReady DEV K3s node join token"
  type        = "SecureString"
  value       = random_password.join_token.result
  overwrite   = true

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-k3s-join-token" })
}

resource "aws_security_group" "k3s" {
  name        = "${var.name_prefix}-k3s"
  description = "Private K3s node communication"
  vpc_id      = var.vpc_id

  egress {
    description = "Required IPv4 outbound through the single NAT Gateway"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-k3s" })
}

resource "aws_vpc_security_group_ingress_rule" "k3s_api" {
  security_group_id            = aws_security_group.k3s.id
  referenced_security_group_id = aws_security_group.k3s.id
  ip_protocol                  = "tcp"
  from_port                    = 6443
  to_port                      = 6443
  description                  = "K3s API between cluster nodes"
}

resource "aws_vpc_security_group_ingress_rule" "flannel" {
  security_group_id            = aws_security_group.k3s.id
  referenced_security_group_id = aws_security_group.k3s.id
  ip_protocol                  = "udp"
  from_port                    = 8472
  to_port                      = 8472
  description                  = "Flannel VXLAN between cluster nodes"
}

resource "aws_vpc_security_group_ingress_rule" "kubelet" {
  security_group_id            = aws_security_group.k3s.id
  referenced_security_group_id = aws_security_group.k3s.id
  ip_protocol                  = "tcp"
  from_port                    = 10250
  to_port                      = 10250
  description                  = "Kubelet API between cluster nodes"
}

resource "aws_iam_role" "server" {
  name = "${var.name_prefix}-k3s-server"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role" "worker" {
  name               = "${var.name_prefix}-k3s-worker"
  assume_role_policy = aws_iam_role.server.assume_role_policy
  tags               = var.common_tags
}

resource "aws_iam_role_policy_attachment" "server_ssm" {
  role       = aws_iam_role.server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "worker_ssm" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "server" {
  name = "${var.name_prefix}-k3s-server"
  role = aws_iam_role.server.name
}

resource "aws_iam_instance_profile" "worker" {
  name = "${var.name_prefix}-k3s-worker"
  role = aws_iam_role.worker.name
}

resource "aws_iam_role_policy" "server_bootstrap" {
  name = "${var.name_prefix}-k3s-server-bootstrap"
  role = aws_iam_role.server.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = local.join_token_policy
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"]
        Resource = var.ecr_repository_arns
      },
    ]
  })
}

resource "aws_iam_role_policy" "worker_bootstrap" {
  name = "${var.name_prefix}-k3s-worker-bootstrap"
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = local.join_token_policy
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"]
        Resource = var.ecr_repository_arns
      },
    ]
  })
}

resource "aws_instance" "server" {
  ami                         = data.aws_ssm_parameter.ubuntu_ami.value
  instance_type               = var.instance_type
  key_name                    = var.ec2_key_name
  subnet_id                   = var.private_app_subnet_ids[0]
  private_ip                  = local.server_ip
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.k3s.id]
  iam_instance_profile        = aws_iam_instance_profile.server.name
  user_data                   = local.server_user_data

  root_block_device {
    encrypted   = true
    volume_size = var.root_volume_size
    volume_type = "gp3"
  }

  depends_on = [
    aws_ssm_parameter.join_token,
    aws_iam_role_policy.server_bootstrap,
    aws_iam_role_policy_attachment.server_ssm,
  ]
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-k3s-server", Role = "server" })
}

resource "aws_instance" "worker" {
  ami                         = data.aws_ssm_parameter.ubuntu_ami.value
  instance_type               = var.instance_type
  key_name                    = var.ec2_key_name
  subnet_id                   = var.private_app_subnet_ids[1]
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.k3s.id]
  iam_instance_profile        = aws_iam_instance_profile.worker.name
  user_data                   = local.worker_user_data

  root_block_device {
    encrypted   = true
    volume_size = var.root_volume_size
    volume_type = "gp3"
  }

  depends_on = [
    aws_instance.server,
    aws_iam_role_policy.worker_bootstrap,
    aws_iam_role_policy_attachment.worker_ssm,
  ]
  tags = merge(var.common_tags, { Name = "${var.name_prefix}-k3s-worker", Role = "worker" })
}
