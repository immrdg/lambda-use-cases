output "topic_arn" {
  description = "ARN of the created SNS Topic"
  value       = aws_sns_topic.this.arn
}

output "topic_name" {
  description = "Name of the created SNS Topic"
  value       = aws_sns_topic.this.name
}
