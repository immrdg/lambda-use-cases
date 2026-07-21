resource "aws_cloudwatch_event_rule" "this" {
  name                = var.rule_name
  description         = var.description
  schedule_expression = var.schedule_expression

  tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "Terragrunt"
    },
    var.tags
  )
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.this.name
  target_id = "TargetLambda"
  arn       = var.target_lambda_arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.target_lambda_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.this.arn
}
