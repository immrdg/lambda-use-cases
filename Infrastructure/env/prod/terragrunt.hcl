include "root" {
  path   = find_in_parent_folders("terragrunt.hcl")
  expose = true
}

terraform {
  source = "../../..//Infrastructure/app"
}

inputs = {
  environment        = "prod"
  aws_region         = "us-east-1"
  profile            = "immrdg21"
  lambda_timeout     = 120
  lambda_memory_size = 256
  force_destroy      = false

  # Assignment 1 — S3 Cleanup
  bucket_name            = "s3-cleanup-bucket-prod-use-case-1"
  s3_retention_days      = 30
  s3_schedule_expression = "cron(0 2 * * ? *)"

  # Assignment 2 — EBS Snapshot
  ebs_retention_days      = 30
  ebs_schedule_expression = "cron(0 2 ? * SUN *)"

  # Assignment 6 — S3 Public Access Audit & SNS Alert (Event-Driven)
  sns_subscription_emails = ["d.gireesh21@gmail.com"]

  common_tags = {
    Environment = "prod"
    Project     = "lambda-automation"
    ManagedBy   = "Terragrunt"
  }
}
