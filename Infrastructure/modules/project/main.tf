module "s3" {
  source        = "../s3"
  bucket_name   = var.bucket_name
  environment   = var.environment
  force_destroy = var.force_destroy
  tags          = var.common_tags
}

locals {
  bucket_arn = "arn:aws:s3:::${var.bucket_name}"
}

module "lambda" {
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
    RETENTION_DAYS = tostring(var.retention_days)
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

module "eventbridge" {
  source              = "../eventbridge"
  rule_name           = "s3-cleanup-${var.environment}-schedule"
  description         = "Triggers S3 cleanup Lambda function periodically"
  schedule_expression = var.schedule_expression
  target_lambda_arn   = module.lambda.function_arn
  target_lambda_name  = module.lambda.function_name
  environment         = var.environment
  tags                = var.common_tags
}
