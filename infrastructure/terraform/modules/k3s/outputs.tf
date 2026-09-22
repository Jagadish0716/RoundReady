output "server_instance_id" {
  description = "K3s server/control-plane EC2 instance ID."
  value       = aws_instance.server.id
}

output "worker_instance_id" {
  description = "K3s worker EC2 instance ID."
  value       = aws_instance.worker.id
}

output "server_private_ip" {
  description = "Private IPv4 address used by the K3s API and worker bootstrap."
  value       = aws_instance.server.private_ip
}

output "worker_private_ip" {
  description = "Private IPv4 address assigned to the K3s worker."
  value       = aws_instance.worker.private_ip
}

output "security_group_id" {
  description = "Security group shared by both private K3s nodes."
  value       = aws_security_group.k3s.id
}

output "join_token_parameter_name" {
  description = "Terraform-owned SSM SecureString path used by K3s bootstrap."
  value       = aws_ssm_parameter.join_token.name
}
