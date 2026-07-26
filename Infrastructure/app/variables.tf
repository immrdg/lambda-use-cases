variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "profile" {
  description = "AWS Named Profile"
  type        = string
  default     = "immrdg21"
}

variable "environment" {
  description = "Target deployment environment"
  type        = string
}

# ── S3 Cleanup ────────────────────────────────────────────────────────────────
variable "bucket_name" {
  description = "Name of the S3 cleanup bucket"
  type        = string
}

variable "s3_retention_days" {
  description = "Retention period for S3 object cleanup in days"
  type        = number
  default     = 30
}

variable "s3_schedule_expression" {
  description = "EventBridge schedule for S3 cleanup Lambda"
  type        = string
  default     = "rate(1 day)"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 128
}

variable "force_destroy" {
  description = "Force destroy S3 bucket"
  type        = bool
  default     = true
}

# ── EBS Snapshot ──────────────────────────────────────────────────────────────
variable "ebs_retention_days" {
  description = "Retention period for EBS snapshots in days"
  type        = number
  default     = 30
}

variable "ebs_schedule_expression" {
  description = "EventBridge schedule for EBS snapshot Lambda"
  type        = string
  default     = "rate(7 days)"
}

# ── S3 Public Access Audit ───────────────────────────────────────────────────
variable "sns_subscription_emails" {
  description = "Set of email addresses to receive S3 security alerts via SNS"
  type        = set(string)
  default     = ["d.gireesh21@gmail.com"]
}

variable "common_tags" {
  description = "Common tags for resources"
  type        = map(string)
  default     = {}
}
