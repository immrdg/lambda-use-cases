locals {
  bucket_arn = "arn:aws:s3:::${var.bucket_name}"
}

# ── Assignment 1: S3 Cleanup ──────────────────────────────────────────────────
module "s3" {
  source        = "../s3"
  bucket_name   = var.bucket_name
  environment   = var.environment
  force_destroy = var.force_destroy
  tags          = var.common_tags
}

module "s3_cleanup_lambda" {
  source        = "../lambda"
  function_name = "s3-cleanup-${var.environment}"
  source_dir    = "${path.module}/../../../lambdas/s3-cleanup"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size
  environment   = var.environment

  environment_variables = {
    BUCKET_NAME    = var.bucket_name
    RETENTION_DAYS = tostring(var.s3_retention_days)
  }

  custom_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3ListBucketAccess"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = local.bucket_arn
      },
      {
        Sid      = "S3DeleteObjectAccess"
        Effect   = "Allow"
        Action   = ["s3:DeleteObject"]
        Resource = "${local.bucket_arn}/*"
      }
    ]
  })

  tags = var.common_tags
}

module "s3_cleanup_schedule" {
  source              = "../eventbridge"
  rule_name           = "s3-cleanup-${var.environment}-schedule"
  description         = "Triggers S3 cleanup Lambda daily"
  schedule_expression = var.s3_schedule_expression
  target_lambda_arn   = module.s3_cleanup_lambda.function_arn
  target_lambda_name  = module.s3_cleanup_lambda.function_name
  environment         = var.environment
  tags                = var.common_tags
}

# ── Assignment 2: EBS Snapshot ────────────────────────────────────────────────
module "ebs_volume" {
  source            = "../ebs"
  volume_name       = "ebs-backup-${var.environment}"
  availability_zone = "${var.aws_region}a"
  size              = 1
  volume_type       = "gp3"
  environment       = var.environment
  tags              = var.common_tags
}

module "ebs_snapshot_lambda" {
  source        = "../lambda"
  function_name = "ebs-snapshot-${var.environment}"
  source_dir    = "${path.module}/../../../lambdas/ebs-snapshot"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 128
  environment   = var.environment

  environment_variables = {
    VOLUME_ID      = module.ebs_volume.volume_id
    RETENTION_DAYS = tostring(var.ebs_retention_days)
  }

  custom_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EBSSnapshotAccess"
        Effect = "Allow"
        Action = [
          "ec2:CreateSnapshot",
          "ec2:DescribeSnapshots",
          "ec2:DeleteSnapshot",
          "ec2:CreateTags"
        ]
        Resource = "*"
      },
      {
        Sid      = "STSGetCallerIdentity"
        Effect   = "Allow"
        Action   = ["sts:GetCallerIdentity"]
        Resource = "*"
      }
    ]
  })

  tags = var.common_tags
}

module "ebs_snapshot_schedule" {
  source              = "../eventbridge"
  rule_name           = "ebs-snapshot-${var.environment}-schedule"
  description         = "Triggers EBS snapshot Lambda weekly"
  schedule_expression = var.ebs_schedule_expression
  target_lambda_arn   = module.ebs_snapshot_lambda.function_arn
  target_lambda_name  = module.ebs_snapshot_lambda.function_name
  environment         = var.environment
  tags                = var.common_tags
}
