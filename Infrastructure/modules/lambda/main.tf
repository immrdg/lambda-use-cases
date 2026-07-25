locals {
  # CI builds and commits lambdas/<name>/lambda-function.zip
  zip_path = "${var.source_dir}/lambda-function.zip"
}

resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "Terragrunt"
    },
    var.tags
  )
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "custom_policy" {
  count  = var.custom_policy_json != null && var.custom_policy_json != "" ? 1 : 0
  name   = "${var.function_name}-policy"
  role   = aws_iam_role.lambda_role.id
  policy = var.custom_policy_json
}

resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "Terragrunt"
    },
    var.tags
  )
}

resource "aws_lambda_function" "this" {
  filename         = local.zip_path
  function_name    = var.function_name
  role             = aws_iam_role.lambda_role.arn
  handler          = var.handler
  runtime          = var.runtime
  timeout          = var.timeout
  memory_size      = var.memory_size
  source_code_hash = filebase64sha256(local.zip_path)

  environment {
    variables = var.environment_variables
  }

  depends_on = [
    aws_iam_role_policy_attachment.basic_execution,
    aws_cloudwatch_log_group.lambda_log_group
  ]

  tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "Terragrunt"
    },
    var.tags
  )
}
