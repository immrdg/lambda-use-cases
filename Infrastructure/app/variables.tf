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

variable "bucket_name" {
  description = "Name of the S3 cleanup bucket"
  type        = string
}

variable "retention_days" {
  description = "Retention period for S3 objects in days"
  type        = number
  default     = 30
}

variable "schedule_expression" {
  description = "Schedule expression for EventBridge trigger"
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

variable "common_tags" {
  description = "Common tags for resources"
  type        = map(string)
  default     = {}
}
