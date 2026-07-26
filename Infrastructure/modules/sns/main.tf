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
  count     = var.subscription_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.this.arn
  protocol  = "email"
  endpoint  = var.subscription_email
}
