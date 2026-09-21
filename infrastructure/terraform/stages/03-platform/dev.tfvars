aws_region            = "ap-south-1"
environment           = "dev"
project_name          = "roundready"
state_bucket          = "roundready-terraform-state-jagadish"
state_region          = "ap-south-1"
network_state_key     = "dev/01-network/terraform.tfstate"
k3s_instance_type     = "t4g.small"
k3s_root_volume_size  = 30
k3s_ami_ssm_parameter = "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id"
ec2_key_name          = "geekyants"
common_tags           = { CostCenter = "development" }
