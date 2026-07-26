terraform {
  required_version = ">= 1.0"
  backend "local" {}
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.profile
}

module "project" {
  source = "../modules/project"

  environment             = var.environment
  aws_region              = var.aws_region
  bucket_name             = var.bucket_name
  s3_retention_days       = var.s3_retention_days
  s3_schedule_expression  = var.s3_schedule_expression
  lambda_timeout          = var.lambda_timeout
  lambda_memory_size      = var.lambda_memory_size
  force_destroy           = var.force_destroy
  ebs_retention_days      = var.ebs_retention_days
  ebs_schedule_expression = var.ebs_schedule_expression
  sns_subscription_emails = var.sns_subscription_emails
  common_tags             = var.common_tags
}
