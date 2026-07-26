variable "topic_name" {
  description = "Name of the SNS Topic"
  type        = string
}

variable "subscription_email" {
  description = "Optional email address to subscribe to the SNS Topic"
  type        = string
  default     = ""
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
