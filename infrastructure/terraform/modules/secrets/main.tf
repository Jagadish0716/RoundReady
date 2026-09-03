resource "aws_secretsmanager_secret" "this" {
  for_each = var.secrets

  name                    = "${var.name_prefix}-${replace(each.key, "_", "-")}"
  description             = each.value.description
  recovery_window_in_days = var.recovery_window_days

  tags = merge(var.common_tags, {
    Name        = "${var.name_prefix}-${replace(each.key, "_", "-")}"
    SecretOwner = each.value.owner
  })
}
