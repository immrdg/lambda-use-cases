include "root" {
  path   = find_in_parent_folders("terragrunt.hcl")
  expose = true
}

terraform {
  source = "../../..//Infrastructure/app"
}

inputs = {
  environment         = "dev"
  aws_region          = "us-east-1"
  profile             = "immrdg21"
  bucket_name         = "s3-cleanup-bucket-dev-use-case-1"
  retention_days      = 30
  schedule_expression = "rate(1 day)"
  lambda_timeout      = 60
  lambda_memory_size  = 128
  force_destroy       = true

  common_tags = {
    Environment = "dev"
    Project     = "lambda-automation"
    ManagedBy   = "Terragrunt"
  }
}
