# MVP Monitoring Configuration (Free Tier Services Only)
# This file contains monitoring for S3, Lambda, and SNS only

# CloudWatch Dashboard for MVP services
resource "aws_cloudwatch_dashboard" "mvp_dashboard" {
  dashboard_name = "${var.project_name}-mvp-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.data_ingestion.function_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            [".", "Throttles", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Function Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "NumberOfObjects", "BucketName", aws_s3_bucket.ohlcv_data.bucket, "StorageType", "AllStorageTypes"],
            [".", "BucketSizeBytes", ".", ".", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "S3 Storage Metrics"
          period  = 86400
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '${aws_cloudwatch_log_group.lambda_logs.name}' | fields @timestamp, @message | sort @timestamp desc | limit 100"
          region  = var.aws_region
          title   = "Recent Lambda Logs"
        }
      }
    ]
  })

  depends_on = [
    aws_lambda_function.data_ingestion,
    aws_s3_bucket.ohlcv_data,
    aws_cloudwatch_log_group.lambda_logs
  ]
}

# Lambda error alarm
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.data_ingestion.function_name
  }

  tags = local.common_tags
}

# Lambda duration alarm (for timeout issues)
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.project_name}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "240000"  # 4 minutes (our timeout is 5 minutes)
  alarm_description   = "This metric monitors lambda duration approaching timeout"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.data_ingestion.function_name
  }

  tags = local.common_tags
}

# Lambda throttle alarm
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.project_name}-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors lambda throttling"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.data_ingestion.function_name
  }

  tags = local.common_tags
}

# Budget alert (already defined in main-mvp.tf, but adding CloudWatch integration)
resource "aws_cloudwatch_metric_alarm" "high_costs" {
  alarm_name          = "${var.project_name}-high-costs"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"  # Daily check
  statistic           = "Maximum"
  threshold           = "4"      # Alert at $4 (before hitting $5 limit)
  alarm_description   = "Alert when estimated charges exceed $4"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = local.common_tags
}

# CloudWatch log group metric filter for API errors
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "${var.project_name}-api-errors"
  log_group_name = aws_cloudwatch_log_group.lambda_logs.name
  pattern        = "[timestamp, uuid, level=\"ERROR\", ...]"

  metric_transformation {
    name      = "APIErrors"
    namespace = "${var.project_name}/Custom"
    value     = "1"
  }
}

# Alarm for API errors
resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  alarm_name          = "${var.project_name}-api-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "APIErrors"
  namespace           = "${var.project_name}/Custom"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "High rate of API errors detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = local.common_tags
}

# Simple health check for data freshness (custom metric)
resource "aws_cloudwatch_log_metric_filter" "successful_ingestion" {
  name           = "${var.project_name}-successful-ingestion"
  log_group_name = aws_cloudwatch_log_group.lambda_logs.name
  pattern        = "[timestamp, uuid, level=\"INFO\", message=\"Successfully processed*\"]"

  metric_transformation {
    name      = "SuccessfulIngestions"
    namespace = "${var.project_name}/Custom"
    value     = "1"
  }
}

# Alarm for no successful ingestions (data staleness)
resource "aws_cloudwatch_metric_alarm" "no_successful_ingestion" {
  alarm_name          = "${var.project_name}-no-data-ingestion"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "SuccessfulIngestions"
  namespace           = "${var.project_name}/Custom"
  period              = "3600"  # 1 hour periods
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "No successful data ingestion detected for 3 hours"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "breaching"

  tags = local.common_tags
}

# Output the dashboard URL
output "cloudwatch_dashboard_url" {
  description = "URL to CloudWatch dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.mvp_dashboard.dashboard_name}"
}
