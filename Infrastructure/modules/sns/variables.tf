variable "topic_name" {
  description = "Name of the SNS Topic"
  type        = string
}

variable "subscription_emails" {
  description = "Set of email addresses to subscribe to the SNS Topic"
  type        = set(string)
  default     = []
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
