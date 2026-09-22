aws_region                 = "ap-south-1"
environment                = "dev"
project_name               = "roundready"
state_bucket               = "roundready-terraform-state-jagadish"
state_region               = "ap-south-1"
network_state_key          = "dev/01-network/terraform.tfstate"
platform_state_key         = "dev/03-platform/terraform.tfstate"
frontend_target_port       = 30080
frontend_health_check_path = "/"
common_tags                = { CostCenter = "development" }
