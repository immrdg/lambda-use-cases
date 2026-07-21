variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "source_dir" {
  description = "Source code directory to package into zip"
  type        = string
}

variable "handler" {
  description = "Function entrypoint handler"
  type        = string
  default     = "index.lambda_handler"
}

variable "runtime" {
  description = "Lambda runtime engine"
  type        = string
  default     = "python3.12"
}

variable "timeout" {
  description = "Execution timeout in seconds"
  type        = number
  default     = 60
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 128
}

variable "environment" {
  description = "Target deployment environment"
  type        = string
  default     = "dev"
}

variable "environment_variables" {
  description = "Map of environment variables to pass to Lambda"
  type        = map(string)
  default     = {}
}

variable "custom_policy_json" {
  description = "Optional JSON string for least-privilege inline IAM policy"
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "Retention period for CloudWatch logs in days"
  type        = number
  default     = 14
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
