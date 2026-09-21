aws_region                       = "ap-south-1"
environment                      = "dev"
project_name                     = "roundready"
ecr_image_tag_mutability         = "IMMUTABLE"
ecr_scan_on_push                 = true
ecr_tagged_image_retention_count = 10
ecr_untagged_retention_days      = 7
ecr_force_delete                 = true
common_tags                      = { CostCenter = "development" }
