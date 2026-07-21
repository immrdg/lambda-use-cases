output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.this.arn
}

output "role_name" {
  description = "Name of the IAM Role created for Lambda"
  value       = aws_iam_role.lambda_role.name
}

output "role_arn" {
  description = "ARN of the IAM Role created for Lambda"
  value       = aws_iam_role.lambda_role.arn
}
