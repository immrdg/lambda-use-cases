# ── Assignment 1 ──────────────────────────────────────────────────────────────
output "bucket_id" {
  description = "S3 cleanup bucket ID"
  value       = module.project.bucket_id
}

output "s3_cleanup_function_name" {
  description = "S3 cleanup Lambda function name"
  value       = module.project.s3_cleanup_function_name
}

output "s3_cleanup_function_arn" {
  description = "S3 cleanup Lambda function ARN"
  value       = module.project.s3_cleanup_function_arn
}

# ── Assignment 2 ──────────────────────────────────────────────────────────────
output "ebs_volume_id" {
  description = "EBS volume ID managed by Terraform"
  value       = module.project.ebs_volume_id
}

output "ebs_snapshot_function_name" {
  description = "EBS snapshot Lambda function name"
  value       = module.project.ebs_snapshot_function_name
}

output "ebs_snapshot_function_arn" {
  description = "EBS snapshot Lambda function ARN"
  value       = module.project.ebs_snapshot_function_arn
}

# ── Assignment 3 ──────────────────────────────────────────────────────────────
output "auto_tagging_ec2_function_name" {
  description = "Auto-Tagging EC2 Lambda function name"
  value       = module.project.auto_tagging_ec2_function_name
}

output "auto_tagging_ec2_function_arn" {
  description = "Auto-Tagging EC2 Lambda function ARN"
  value       = module.project.auto_tagging_ec2_function_arn
}

output "auto_tagging_ec2_rule_name" {
  description = "Auto-Tagging EC2 EventBridge rule name"
  value       = module.project.auto_tagging_ec2_rule_name
}
