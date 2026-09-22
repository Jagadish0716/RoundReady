variable "name_prefix" {
  description = "Environment-qualified resource name prefix."
  type        = string
}

variable "aws_region" {
  description = "Region used by bootstrap scripts for AWS API calls."
  type        = string
}

variable "vpc_id" {
  description = "VPC for the private K3s nodes and their security group."
  type        = string
}

variable "private_app_subnet_ids" {
  description = "Two private application subnets, one per K3s node."
  type        = list(string)

  validation {
    condition     = length(var.private_app_subnet_ids) == 2
    error_message = "K3s requires exactly two private application subnet IDs."
  }
}

variable "instance_type" {
  description = "ARM64-compatible EC2 instance type for both development K3s nodes."
  type        = string
  default     = "t4g.small"
}

variable "root_volume_size" {
  description = "Encrypted gp3 root-volume size in GiB for each K3s node."
  type        = number
  default     = 30
}

variable "ami_ssm_parameter" {
  description = "AWS SSM public parameter resolving the supported Ubuntu ARM64 AMI."
  type        = string
}

variable "ec2_key_name" {
  description = "Name of an existing EC2 key pair. The private key is never read by Terraform."
  type        = string
}

variable "ecr_repository_arns" {
  description = "RoundReady ECR repository ARNs allowed for image pulls."
  type        = list(string)
}

variable "common_tags" {
  description = "Common non-sensitive resource tags."
  type        = map(string)
  default     = {}
}
