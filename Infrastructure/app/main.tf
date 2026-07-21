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

  environment         = var.environment
  bucket_name         = var.bucket_name
  retention_days      = var.retention_days
  schedule_expression = var.schedule_expression
  lambda_timeout      = var.lambda_timeout
  lambda_memory_size  = var.lambda_memory_size
  force_destroy       = var.force_destroy
  common_tags         = var.common_tags
}
