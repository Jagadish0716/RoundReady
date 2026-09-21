terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" { use_lockfile = true }
}
variable "aws_region" { type = string }
variable "environment" { type = string }
variable "project_name" { type = string }
variable "state_bucket" { type = string }
variable "state_region" { type = string }
variable "network_state_key" { type = string }
variable "k3s_instance_type" { type = string }
variable "k3s_root_volume_size" { type = number }
variable "k3s_ami_ssm_parameter" { type = string }
variable "ec2_key_name" { type = string }
variable "common_tags" { type = map(string) }
data "terraform_remote_state" "network" {
  backend = "s3"
  config  = { bucket = var.state_bucket, key = var.network_state_key, region = var.state_region }
}
data "aws_ssm_parameter" "ubuntu_ami" { name = var.k3s_ami_ssm_parameter }
data "aws_caller_identity" "current" {}
locals {
  name_prefix      = "${var.project_name}-${var.environment}"
  tags             = merge({ Project = "RoundReady", Environment = var.environment, ManagedBy = "Terraform" }, var.common_tags)
  server_ip        = cidrhost("10.10.16.0/21", 10)
  server_user_data = <<-EOT
    #!/bin/bash
    set -Eeuo pipefail
    apt-get update -y
    apt-get install -y curl awscli openssl snapd
    if ! systemctl is-active --quiet snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null && ! systemctl is-active --quiet amazon-ssm-agent 2>/dev/null; then
      snap install amazon-ssm-agent --classic || true
      systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null || systemctl enable --now amazon-ssm-agent
    fi
    TOKEN="$(openssl rand -hex 32)"
    export K3S_TOKEN="$TOKEN"
    curl -sfL https://get.k3s.io | sh -s - server --write-kubeconfig-mode 644
    aws ssm put-parameter \
      --region ${var.aws_region} \
      --name /${local.name_prefix}/k3s/join-token \
      --type SecureString \
      --value "$TOKEN" \
      --overwrite
    unset K3S_TOKEN TOKEN
  EOT
  worker_user_data = <<-EOT
    #!/bin/bash
    set -Eeuo pipefail
    apt-get update -y
    apt-get install -y curl awscli snapd
    if ! systemctl is-active --quiet snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null && ! systemctl is-active --quiet amazon-ssm-agent 2>/dev/null; then
      snap install amazon-ssm-agent --classic || true
      systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service 2>/dev/null || systemctl enable --now amazon-ssm-agent
    fi
    deadline=$$(($${SECONDS} + 900))
    TOKEN=""
    until [ "$${SECONDS}" -ge "$deadline" ]; do
      TOKEN="$(aws ssm get-parameter \
        --region ${var.aws_region} \
        --name /${local.name_prefix}/k3s/join-token \
        --with-decryption \
        --query Parameter.Value \
        --output text 2>/dev/null || true)"
      if [ -n "$TOKEN" ] && timeout 5 bash -c '</dev/tcp/${local.server_ip}/6443' 2>/dev/null; then
        break
      fi
      TOKEN=""
      sleep 10
    done
    if [ -z "$TOKEN" ]; then
      echo "Timed out waiting for the K3s server token and API" >&2
      exit 1
    fi
    export K3S_URL=https://${local.server_ip}:6443
    export K3S_TOKEN="$TOKEN"
    curl -sfL https://get.k3s.io | sh -
    unset K3S_URL K3S_TOKEN TOKEN
  EOT
}
provider "aws" {
  region = var.aws_region
  default_tags { tags = local.tags }
}
resource "aws_security_group" "k3s" {
  name        = "${local.name_prefix}-k3s"
  description = "Private K3s node communication"
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id
  egress {
    description = "Allow outbound package, SSM, and cluster traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(local.tags, { Name = "${local.name_prefix}-k3s" })
}
resource "aws_vpc_security_group_ingress_rule" "k3s_api" {
  security_group_id            = aws_security_group.k3s.id
  referenced_security_group_id = aws_security_group.k3s.id
  ip_protocol                  = "tcp"
  from_port                    = 6443
  to_port                      = 6443
}
resource "aws_vpc_security_group_ingress_rule" "flannel" {
  security_group_id            = aws_security_group.k3s.id
  referenced_security_group_id = aws_security_group.k3s.id
  ip_protocol                  = "udp"
  from_port                    = 8472
  to_port                      = 8472
}
resource "aws_vpc_security_group_ingress_rule" "kubelet" {
  security_group_id            = aws_security_group.k3s.id
  referenced_security_group_id = aws_security_group.k3s.id
  ip_protocol                  = "tcp"
  from_port                    = 10250
  to_port                      = 10250
}
resource "aws_iam_role" "server" {
  name               = "${local.name_prefix}-k3s-server"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags               = local.tags
}
resource "aws_iam_role" "worker" {
  name               = "${local.name_prefix}-k3s-worker"
  assume_role_policy = aws_iam_role.server.assume_role_policy
  tags               = local.tags
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
  name = "${local.name_prefix}-k3s-server"
  role = aws_iam_role.server.name
}
resource "aws_iam_instance_profile" "worker" {
  name = "${local.name_prefix}-k3s-worker"
  role = aws_iam_role.worker.name
}
resource "aws_iam_role_policy" "server_bootstrap" {
  role   = aws_iam_role.server.id
  name   = "${local.name_prefix}-k3s-server-bootstrap"
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["ssm:GetParameter", "ssm:PutParameter"], Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${local.name_prefix}/k3s/join-token" }, { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" }, { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"], Resource = "arn:aws:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/${local.name_prefix}/*" }] })
}
resource "aws_iam_role_policy" "worker_bootstrap" {
  role   = aws_iam_role.worker.id
  name   = "${local.name_prefix}-k3s-worker-bootstrap"
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["ssm:GetParameter"], Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${local.name_prefix}/k3s/join-token" }, { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" }, { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"], Resource = "arn:aws:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/${local.name_prefix}/*" }] })
}
resource "aws_instance" "server" {
  ami                         = data.aws_ssm_parameter.ubuntu_ami.value
  instance_type               = var.k3s_instance_type
  key_name                    = var.ec2_key_name
  subnet_id                   = data.terraform_remote_state.network.outputs.private_app_subnet_ids[0]
  private_ip                  = local.server_ip
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.k3s.id]
  iam_instance_profile        = aws_iam_instance_profile.server.name
  user_data                   = local.server_user_data
  root_block_device {
    encrypted   = true
    volume_size = var.k3s_root_volume_size
    volume_type = "gp3"
  }
  tags = merge(local.tags, { Name = "${local.name_prefix}-k3s-server", Role = "server" })
}
resource "aws_instance" "worker" {
  ami                         = data.aws_ssm_parameter.ubuntu_ami.value
  instance_type               = var.k3s_instance_type
  key_name                    = var.ec2_key_name
  subnet_id                   = data.terraform_remote_state.network.outputs.private_app_subnet_ids[1]
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.k3s.id]
  iam_instance_profile        = aws_iam_instance_profile.worker.name
  user_data                   = local.worker_user_data
  root_block_device {
    encrypted   = true
    volume_size = var.k3s_root_volume_size
    volume_type = "gp3"
  }
  tags       = merge(local.tags, { Name = "${local.name_prefix}-k3s-worker", Role = "worker" })
  depends_on = [aws_instance.server]
}
output "k3s_server_instance_id" { value = aws_instance.server.id }
output "k3s_worker_instance_id" { value = aws_instance.worker.id }
output "k3s_server_private_ip" { value = aws_instance.server.private_ip }
output "k3s_worker_private_ip" { value = aws_instance.worker.private_ip }
output "k3s_node_security_group_id" { value = aws_security_group.k3s.id }
