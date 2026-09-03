variable "name_prefix" {
  description = "Environment-qualified repository namespace."
  type        = string
}

variable "production_mode" {
  description = "Enforce the production ECR safety baseline."
  type        = bool
}

variable "components" {
  description = "Deployable components receiving independent private repositories."
  type        = list(string)

  validation {
    condition     = length(var.components) > 0 && length(distinct(var.components)) == length(var.components)
    error_message = "components must be a non-empty list without duplicates."
  }
}

variable "image_tag_mutability" {
  description = "ECR image-tag mutability mode."
  type        = string
  default     = "IMMUTABLE"

  validation {
    condition     = contains(["IMMUTABLE", "MUTABLE"], var.image_tag_mutability)
    error_message = "image_tag_mutability must be IMMUTABLE or MUTABLE."
  }
}

variable "scan_on_push" {
  description = "Enable ECR basic vulnerability scanning when images are pushed."
  type        = bool
  default     = true
}

variable "tagged_image_retention_count" {
  description = "Number of recent tagged images retained for rollback."
  type        = number

  validation {
    condition     = var.tagged_image_retention_count >= 5 && floor(var.tagged_image_retention_count) == var.tagged_image_retention_count
    error_message = "tagged_image_retention_count must be an integer of at least five."
  }
}

variable "untagged_retention_days" {
  description = "Days to retain untagged images."
  type        = number

  validation {
    condition     = var.untagged_retention_days >= 1 && floor(var.untagged_retention_days) == var.untagged_retention_days
    error_message = "untagged_retention_days must be a positive integer."
  }
}

variable "force_delete" {
  description = "Allow repository deletion while it contains images; must be false in production."
  type        = bool
  default     = false
}

variable "common_tags" {
  description = "Non-sensitive repository tags."
  type        = map(string)
  default     = {}
}
