resource "aws_ecr_repository" "this" {
  for_each = toset(var.components)

  name                 = "${var.name_prefix}/${each.value}"
  image_tag_mutability = var.image_tag_mutability
  force_delete         = var.force_delete

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  lifecycle {
    precondition {
      condition     = !var.production_mode || (var.image_tag_mutability == "IMMUTABLE" && !var.force_delete && var.scan_on_push)
      error_message = "Production ECR requires immutable tags, scan on push, and force_delete disabled."
    }
  }

  tags = merge(var.common_tags, {
    Name      = "${var.name_prefix}/${each.value}"
    Component = each.value
  })
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each = aws_ecr_repository.this

  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after ${var.untagged_retention_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.untagged_retention_days
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Retain the newest ${var.tagged_image_retention_count} tagged images"
        selection = {
          tagStatus      = "tagged"
          tagPatternList = ["*"]
          countType      = "imageCountMoreThan"
          countNumber    = var.tagged_image_retention_count
        }
        action = { type = "expire" }
      },
    ]
  })
}
