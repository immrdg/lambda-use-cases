# Root terragrunt configuration
# Uses local backend matching MyAWSInfraProj1 design.

locals {
  aws_region  = "us-east-1"
  aws_profile = "immrdg21"
  project     = "lambda-automation"
}

remote_state {
  backend = "local"
  config = {
    path = "${path_relative_to_include()}/terraform.tfstate"
  }
}

inputs = {
  project_name = "lambda-automation"
  profile      = "immrdg21"
  aws_region   = "us-east-1"
  common_tags = {
    Terraform = "true"
    ManagedBy = "Terragrunt"
  }
}
