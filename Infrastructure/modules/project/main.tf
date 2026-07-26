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
  source               = "../lambda"
  function_name        = "s3-cleanup-${var.environment}"
  source_dir           = "${path.module}/../../../lambdas/s3-cleanup"
  handler              = "handler.lambda_handler"
  runtime              = "python3.12"
  timeout              = var.lambda_timeout
  memory_size          = var.lambda_memory_size
  environment          = var.environment
  enable_custom_policy = true

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
  source               = "../lambda"
  function_name        = "ebs-snapshot-${var.environment}"
  source_dir           = "${path.module}/../../../lambdas/ebs-snapshot"
  handler              = "handler.lambda_handler"
  runtime              = "python3.12"
  timeout              = 60
  memory_size          = 128
  environment          = var.environment
  enable_custom_policy = true

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

# ── Assignment 3: Auto-Tagging EC2 Instances ──────────────────────────────────
module "auto_tagging_ec2_lambda" {
  source               = "../lambda"
  function_name        = "auto-tagging-ec2-${var.environment}"
  source_dir           = "${path.module}/../../../lambdas/auto-tagging-ec2"
  handler              = "handler.lambda_handler"
  runtime              = "python3.12"
  timeout              = 60
  memory_size          = 128
  environment          = var.environment
  enable_custom_policy = true

  environment_variables = {
    ENVIRONMENT   = var.environment
    DEFAULT_OWNER = "DevOpsTeam"
  }

  custom_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EC2AutoTaggingAccess"
        Effect = "Allow"
        Action = [
          "ec2:CreateTags",
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      },
      {
        Sid      = "CloudTrailLookupAccess"
        Effect   = "Allow"
        Action   = ["cloudtrail:LookupEvents"]
        Resource = "*"
      }
    ]
  })

  tags = var.common_tags
}

module "auto_tagging_ec2_rule" {
  source             = "../eventbridge"
  rule_name          = "auto-tagging-ec2-${var.environment}-rule"
  description        = "Triggers auto-tagging Lambda when an EC2 instance enters running state"
  event_pattern      = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Instance State-change Notification"]
    detail      = {
      state = ["running"]
    }
  })
  target_lambda_arn  = module.auto_tagging_ec2_lambda.function_arn
  target_lambda_name = module.auto_tagging_ec2_lambda.function_name
  environment        = var.environment
  tags               = var.common_tags
}

# ── Assignment 6: Audit S3 Buckets for Public Access ──────────────────────────
module "s3_audit_sns" {
  source              = "../sns"
  topic_name          = "s3-public-audit-${var.environment}-alerts"
  subscription_emails = var.sns_subscription_emails
  environment         = var.environment
  tags                = var.common_tags
}

module "s3_public_audit_lambda" {
  source               = "../lambda"
  function_name        = "s3-public-audit-${var.environment}"
  source_dir           = "${path.module}/../../../lambdas/s3-public-audit"
  handler              = "handler.lambda_handler"
  runtime              = "python3.12"
  timeout              = 60
  memory_size          = 128
  environment          = var.environment
  enable_custom_policy = true

  environment_variables = {
    ENVIRONMENT   = var.environment
    SNS_TOPIC_ARN = module.s3_audit_sns.topic_arn
  }

  custom_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3PublicAuditAccess"
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets",
          "s3:GetBucketPublicAccessBlock",
          "s3:GetBucketPolicyStatus",
          "s3:GetBucketAcl"
        ]
        Resource = "*"
      },
      {
        Sid      = "SNSPublishAlertAccess"
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = module.s3_audit_sns.topic_arn
      }
    ]
  })

  tags = var.common_tags
}

module "s3_public_audit_rule" {
  source        = "../eventbridge"
  rule_name     = "s3-public-audit-${var.environment}-rule"
  description   = "Triggers S3 public access audit Lambda whenever S3 security settings are modified"
  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["AWS API Call via CloudTrail"]
    detail      = {
      eventName = [
        "PutBucketPublicAccessBlock",
        "DeleteBucketPublicAccessBlock",
        "PutBucketPolicy",
        "DeleteBucketPolicy",
        "PutBucketAcl"
      ]
    }
  })
  target_lambda_arn  = module.s3_public_audit_lambda.function_arn
  target_lambda_name = module.s3_public_audit_lambda.function_name
  environment        = var.environment
  tags               = var.common_tags
}
