resource "aws_ebs_volume" "this" {
  availability_zone = var.availability_zone
  size              = var.size
  type              = var.volume_type

  tags = merge(
    {
      Name        = var.volume_name
      Environment = var.environment
      ManagedBy   = "Terragrunt"
    },
    var.tags
  )
}
