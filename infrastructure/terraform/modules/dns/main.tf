data "aws_route53_zone" "existing" {
  count = var.enabled && var.hosted_zone_id == null ? 1 : 0

  name         = coalesce(var.hosted_zone_name, "invalid.invalid")
  private_zone = false

  lifecycle {
    precondition {
      condition     = try(trimspace(var.hosted_zone_name), "") != ""
      error_message = "hosted_zone_name is required when public ingress is enabled without hosted_zone_id."
    }
  }
}

locals {
  hosted_zone_id  = var.enabled ? coalesce(var.hosted_zone_id, try(data.aws_route53_zone.existing[0].zone_id, null)) : null
  alb_alias_ready = var.enabled && var.alb_dns_name != null && var.alb_zone_id != null
}

check "alb_alias_inputs" {
  assert {
    condition     = (var.alb_dns_name == null) == (var.alb_zone_id == null)
    error_message = "alb_dns_name and alb_zone_id must be supplied together."
  }
}

resource "aws_acm_certificate" "this" {
  count = var.enabled ? 1 : 0

  domain_name               = coalesce(var.frontend_domain, "invalid.invalid")
  subject_alternative_names = var.api_domain == null ? [] : [var.api_domain]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true

    precondition {
      condition = (
        var.frontend_domain != null &&
        var.api_domain != null &&
        try(trimspace(var.frontend_domain), "") != "" &&
        try(trimspace(var.api_domain), "") != "" &&
        var.frontend_domain != var.api_domain &&
        (var.hosted_zone_id != null || var.hosted_zone_name != null)
      )
      error_message = "Enabled public ingress requires distinct frontend_domain and api_domain values plus an existing hosted zone ID or name."
    }
  }

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-public-tls" })
}

resource "aws_route53_record" "certificate_validation" {
  for_each = var.enabled ? {
    for option in aws_acm_certificate.this[0].domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      record = option.resource_record_value
      type   = option.resource_record_type
    }
  } : {}

  allow_overwrite = true
  zone_id         = local.hosted_zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 300
  records         = [each.value.record]
}

resource "aws_acm_certificate_validation" "this" {
  count = var.enabled ? 1 : 0

  certificate_arn         = aws_acm_certificate.this[0].arn
  validation_record_fqdns = [for record in aws_route53_record.certificate_validation : record.fqdn]
}

resource "aws_route53_record" "public_alias" {
  for_each = local.alb_alias_ready ? {
    frontend = coalesce(var.frontend_domain, "")
    api      = coalesce(var.api_domain, "")
  } : {}

  zone_id = local.hosted_zone_id
  name    = each.value
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}
