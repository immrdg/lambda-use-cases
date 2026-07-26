resource "aws_sns_topic" "this" {
  name = var.topic_name

  tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "Terragrunt"
    },
    var.tags
  )
}

resource "aws_sns_topic_subscription" "email" {
  for_each  = var.subscription_emails
  topic_arn = aws_sns_topic.this.arn
  protocol  = "email"
  endpoint  = each.value
}
