variable "rule_name" {
  description = "Name of the EventBridge rule"
  type        = string
}

variable "description" {
  description = "Description of the EventBridge rule"
  type        = string
  default     = "Trigger for AWS Lambda function"
}

variable "schedule_expression" {
  description = "Schedule rate or cron expression (e.g., rate(1 day) or cron(0 0 * * ? *))"
  type        = string
  default     = null
}

variable "event_pattern" {
  description = "Event pattern JSON string for pattern matching rules"
  type        = string
  default     = null
}

variable "target_lambda_arn" {
  description = "ARN of the target Lambda function to invoke"
  type        = string
}

variable "target_lambda_name" {
  description = "Name of the target Lambda function to grant permissions to"
  type        = string
}

variable "environment" {
  description = "Target deployment environment"
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
