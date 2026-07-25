# ── Assignment 1 ──────────────────────────────────────────────────────────────
output "bucket_id" {
  value = module.s3.bucket_id
}

output "s3_cleanup_function_name" {
  value = module.s3_cleanup_lambda.function_name
}

output "s3_cleanup_function_arn" {
  value = module.s3_cleanup_lambda.function_arn
}

# ── Assignment 2 ──────────────────────────────────────────────────────────────
output "ebs_volume_id" {
  value = module.ebs_volume.volume_id
}

output "ebs_snapshot_function_name" {
  value = module.ebs_snapshot_lambda.function_name
}

output "ebs_snapshot_function_arn" {
  value = module.ebs_snapshot_lambda.function_arn
}
