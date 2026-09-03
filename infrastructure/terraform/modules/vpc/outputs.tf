output "vpc_id" {
  description = "VPC ID."
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "VPC IPv4 CIDR."
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs for future ALB placement."
  value       = [for az in local.azs : aws_subnet.public[az].id]
}

output "private_app_subnet_ids" {
  description = "Private application subnet IDs for future EKS workloads."
  value       = [for az in local.azs : aws_subnet.private_app[az].id]
}

output "private_data_subnet_ids" {
  description = "Private data subnet IDs for future managed data services."
  value       = [for az in local.azs : aws_subnet.private_data[az].id]
}
