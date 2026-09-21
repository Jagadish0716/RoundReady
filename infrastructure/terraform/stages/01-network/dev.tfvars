aws_region       = "ap-south-1"
environment      = "dev"
project_name     = "roundready"
vpc_cidr         = "10.10.0.0/16"
az_count         = 2
nat_gateway_mode = "single"
enable_flow_logs = false
common_tags      = { CostCenter = "development" }
