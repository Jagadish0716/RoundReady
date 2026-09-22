variable "name_prefix" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "k3s_node_security_group_id" { type = string }
variable "k3s_instance_ids" {
  type = list(string)

  validation {
    condition     = length(var.k3s_instance_ids) == 2
    error_message = "The frontend target group requires exactly the K3s server and worker instance IDs."
  }
}
variable "target_port" {
  type    = number
  default = 30080
}
variable "health_check_path" {
  type    = string
  default = "/"
}
variable "common_tags" {
  type    = map(string)
  default = {}
}
