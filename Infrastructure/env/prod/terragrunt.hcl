include "root" {
  path   = find_in_parent_folders("terragrunt.hcl")
  expose = true
}

terraform {
  source = "../../..//Infrastructure/app"
}

inputs = {
  environment         = "prod"
  aws_region          = "us-east-1"
  profile             = "immrdg21"
  bucket_name         = "s3-cleanup-bucket-prod-use-case-1"
  retention_days      = 30
  schedule_expression = "cron(0 2 * * ? *)"
  lambda_timeout      = 120
  lambda_memory_size  = 256
  force_destroy       = false

  common_tags = {
    Environment = "prod"
    Project     = "lambda-automation"
    ManagedBy   = "Terragrunt"
  }
}
