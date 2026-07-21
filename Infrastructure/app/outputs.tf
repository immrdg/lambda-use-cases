output "bucket_id" {
  description = "The ID of the created S3 bucket"
  value       = module.project.bucket_id
}

output "bucket_arn" {
  description = "The ARN of the created S3 bucket"
  value       = module.project.bucket_arn
}

output "lambda_function_name" {
  description = "The name of the deployed Lambda function"
  value       = module.project.lambda_function_name
}

output "lambda_function_arn" {
  description = "The ARN of the deployed Lambda function"
  value       = module.project.lambda_function_arn
}

output "eventbridge_rule_arn" {
  description = "The ARN of the scheduled EventBridge rule"
  value       = module.project.eventbridge_rule_arn
}
