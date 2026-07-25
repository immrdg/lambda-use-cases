include "root" {
  path   = find_in_parent_folders("terragrunt.hcl")
  expose = true
}

terraform {
  source = "../../..//Infrastructure/app"
}

inputs = {
  environment        = "dev"
  aws_region         = "us-east-1"
  profile            = "immrdg21"
  lambda_timeout     = 60
  lambda_memory_size = 128
  force_destroy      = true

  # Assignment 1 — S3 Cleanup
  bucket_name            = "s3-cleanup-bucket-dev-use-case-1"
  s3_retention_days      = 30
  s3_schedule_expression = "rate(1 day)"

  # Assignment 2 — EBS Snapshot
  ebs_retention_days      = 30
  ebs_schedule_expression = "rate(7 days)"

  common_tags = {
    Environment = "dev"
    Project     = "lambda-automation"
    ManagedBy   = "Terragrunt"
  }
}
