# MVP Configuration for AWS Free Tier
# This file provisions the lean pipeline: data lake bucket, ingestion Lambda,
# EventBridge schedule, SNS alerts, SSM credentials, and the interactive token UI.

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -----------------------------------------------------------------------------
# Variables & Locals
# -----------------------------------------------------------------------------
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "stock-pipeline-mvp"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "notification_email" {
  description = "Email address for SNS notifications"
  type        = string
}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    CostCenter  = "MVP"
  }

  bucket_name = "${var.project_name}-${var.environment}-ohlcv"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# -----------------------------------------------------------------------------
# S3 Data Lake
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "ohlcv_data" {
  bucket = "${local.bucket_name}-${random_id.bucket_suffix.hex}"

  tags = merge(local.common_tags, {
    Name     = "OHLCV Data Lake"
    FreeTier = "Yes"
  })
}

resource "aws_s3_bucket_versioning" "ohlcv_data" {
  bucket = aws_s3_bucket.ohlcv_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ohlcv_data" {
  bucket = aws_s3_bucket.ohlcv_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "ohlcv_data" {
  bucket = aws_s3_bucket.ohlcv_data.id

  rule {
    id     = "standard-retention"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 45
      storage_class = "STANDARD_IA"
    }

    # No expiration - data kept indefinitely
    # After 45 days, data moves to cheaper Infrequent Access storage
    # Cost: ~$0.0125/GB/month (IA) vs $0.023/GB/month (Standard)
  }

  rule {
    id     = "cleanup-incomplete"
    status = "Enabled"

    # Provide an explicit filter to satisfy provider requirement that each rule
    # must have either a `filter` or `prefix` attribute. We scope this rule to
    # the root of the bucket (empty prefix) so it applies to multipart uploads
    # for all objects.
    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Folder placeholders keep S3 prefixes visible in console
resource "aws_s3_object" "raw_placeholder" {
  bucket  = aws_s3_bucket.ohlcv_data.id
  key     = "raw/ohlcv/2025-01-01/.keep"
  content = ""
}

resource "aws_s3_object" "analytics_placeholder" {
  bucket  = aws_s3_bucket.ohlcv_data.id
  key     = "analytics/ohlcv/.keep"
  content = ""
}

# -----------------------------------------------------------------------------
# Notifications & Credentials
# -----------------------------------------------------------------------------
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
  })
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

resource "aws_ssm_parameter" "fyers_refresh_token" {
  name        = "/${var.project_name}/fyers/refresh_token"
  description = "Fyers API refresh token"
  type        = "SecureString"
  value       = "CHANGE_ME"

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
    Purpose  = "API_Credentials"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "fyers_client_id" {
  name        = "/${var.project_name}/fyers/client_id"
  description = "Fyers API client ID"
  type        = "SecureString"
  value       = "CHANGE_ME"

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
    Purpose  = "API_Credentials"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "fyers_app_secret" {
  name        = "/${var.project_name}/fyers/app_secret"
  description = "Fyers API app secret"
  type        = "SecureString"
  value       = "CHANGE_ME"

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
    Purpose  = "API_Credentials"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "fyers_pin" {
  name        = "/${var.project_name}/fyers/pin"
  description = "Fyers API PIN (optional)"
  type        = "SecureString"
  value       = "CHANGE_ME"

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
    Purpose  = "API_Credentials"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "fyers_access_token" {
  name        = "/${var.project_name}/fyers/access_token"
  description = "Fyers API access token (auto-populated by Lambda)"
  type        = "SecureString"
  value       = "AUTO_GENERATED"

  tags = merge(local.common_tags, {
    FreeTier    = "Yes"
    Purpose     = "API_Credentials"
    AutoManaged = "Yes"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-ingestion"
  retention_in_days = 7

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
  })
}

resource "aws_cloudwatch_log_group" "etl_logs" {
  name              = "/aws/lambda/${var.project_name}-etl"
  retention_in_days = 7

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
    Purpose  = "ETL"
  })
}

# -----------------------------------------------------------------------------
# Lambda Packaging Helpers
# -----------------------------------------------------------------------------
resource "null_resource" "lambda_dependencies" {
  triggers = {
    requirements = filemd5("../ingestion/requirements.txt")
    lambda_code  = filemd5("../ingestion/lambda_ingestion.py")
  }

  provisioner "local-exec" {
    command = <<-EOT
      if (Test-Path "../deployment/lambda_package") { Remove-Item "../deployment/lambda_package" -Recurse -Force }
      New-Item -ItemType Directory -Path "../deployment/lambda_package" -Force
      Copy-Item "../ingestion/lambda_ingestion.py" "../deployment/lambda_package/"
      pip install -r "../ingestion/requirements.txt" -t "../deployment/lambda_package" --quiet
      if (Test-Path "../deployment/lambda_ingestion.zip") { Remove-Item "../deployment/lambda_ingestion.zip" -Force }
      Compress-Archive -Path "../deployment/lambda_package/*" -DestinationPath "../deployment/lambda_ingestion.zip"
    EOT

    interpreter = ["powershell", "-Command"]
    working_dir = path.module
  }
}

# Lightweight ETL Lambda packaging (no external dependencies)
resource "null_resource" "etl_lambda_packaging" {
  triggers = {
    etl_code = filemd5("../etl/lightweight_etl.py")
  }

  provisioner "local-exec" {
    command = <<-EOT
      if (Test-Path "../deployment/etl_package") { Remove-Item "../deployment/etl_package" -Recurse -Force }
      New-Item -ItemType Directory -Path "../deployment/etl_package" -Force
      Copy-Item "../etl/lightweight_etl.py" "../deployment/etl_package/"
      if (Test-Path "../deployment/lightweight_etl.zip") { Remove-Item "../deployment/lightweight_etl.zip" -Force }
      Compress-Archive -Path "../deployment/etl_package/*" -DestinationPath "../deployment/lightweight_etl.zip"
    EOT

    interpreter = ["powershell", "-Command"]
    working_dir = path.module
  }
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "../deployment/lambda_ingestion.zip"
  source_dir  = "../deployment/lambda_package"

  depends_on = [null_resource.lambda_dependencies]
}

data "archive_file" "etl_lambda_zip" {
  type        = "zip"
  output_path = "../deployment/lightweight_etl.zip"
  source_dir  = "../deployment/etl_package"

  depends_on = [null_resource.etl_lambda_packaging]
}

resource "null_resource" "token_generator_dependencies" {
  triggers = {
    requirements = filemd5("../aws-token-generator/requirements.txt")
    lambda_code  = filemd5("../aws-token-generator/lambda_function.py")
  }

  provisioner "local-exec" {
    command = <<-EOT
      if (Test-Path "../deployment/token_generator_package") { Remove-Item "../deployment/token_generator_package" -Recurse -Force }
      New-Item -ItemType Directory -Path "../deployment/token_generator_package" -Force
      Copy-Item "../aws-token-generator/lambda_function.py" "../deployment/token_generator_package/"
      pip install -r "../aws-token-generator/requirements.txt" -t "../deployment/token_generator_package" --quiet
      if (Test-Path "../deployment/token_generator.zip") { Remove-Item "../deployment/token_generator.zip" -Force }
      Compress-Archive -Path "../deployment/token_generator_package/*" -DestinationPath "../deployment/token_generator.zip"
    EOT

    interpreter = ["powershell", "-Command"]
    working_dir = path.module
  }
}

data "archive_file" "token_generator_zip" {
  type        = "zip"
  output_path = "../deployment/token_generator.zip"
  source_dir  = "../deployment/token_generator_package"

  depends_on = [null_resource.token_generator_dependencies]
}

# -----------------------------------------------------------------------------
# Lambda Functions
# -----------------------------------------------------------------------------
resource "aws_lambda_function" "data_ingestion" {
  filename         = "../deployment/lambda_ingestion.zip"
  function_name    = "${var.project_name}-ingestion"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "lambda_ingestion.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 300

  environment {
    variables = {
      S3_BUCKET_NAME            = aws_s3_bucket.ohlcv_data.id
      SNS_TOPIC_ARN             = aws_sns_topic.alerts.arn
      FYERS_ACCESS_TOKEN_PARAM  = aws_ssm_parameter.fyers_access_token.name
      FYERS_REFRESH_TOKEN_PARAM = aws_ssm_parameter.fyers_refresh_token.name
      FYERS_CLIENT_ID_PARAM     = aws_ssm_parameter.fyers_client_id.name
      FYERS_APP_SECRET_PARAM    = aws_ssm_parameter.fyers_app_secret.name
      FYERS_PIN_PARAM           = aws_ssm_parameter.fyers_pin.name
      PROJECT_NAME              = var.project_name
      ENVIRONMENT               = var.environment
      ENABLE_TRADING_HOURS_CHECK = "true"
    }
  }

  depends_on = [
    null_resource.lambda_dependencies,
    data.archive_file.lambda_zip,
    aws_cloudwatch_log_group.lambda_logs
  ]

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
  })
}

resource "aws_lambda_function" "lightweight_etl" {
  filename         = "../deployment/lightweight_etl.zip"
  function_name    = "${var.project_name}-etl"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "lightweight_etl.lambda_handler"
  source_code_hash = data.archive_file.etl_lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 600  # 10 minutes for ETL processing
  memory_size      = 512  # More memory for processing

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.ohlcv_data.id
      SNS_TOPIC_ARN  = aws_sns_topic.alerts.arn
      PROJECT_NAME   = var.project_name
      ENVIRONMENT    = var.environment
    }
  }

  depends_on = [
    null_resource.etl_lambda_packaging,
    data.archive_file.etl_lambda_zip,
    aws_cloudwatch_log_group.etl_logs
  ]

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
    Purpose  = "ETL"
  })
}

resource "aws_lambda_function" "token_generator" {
  filename         = "../deployment/token_generator.zip"
  function_name    = "${var.project_name}-token-generator"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.token_generator_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      FYERS_ACCESS_TOKEN_PARAM  = aws_ssm_parameter.fyers_access_token.name
      FYERS_REFRESH_TOKEN_PARAM = aws_ssm_parameter.fyers_refresh_token.name
      FYERS_CLIENT_ID_PARAM     = aws_ssm_parameter.fyers_client_id.name
      FYERS_APP_SECRET_PARAM    = aws_ssm_parameter.fyers_app_secret.name
      PROJECT_NAME              = var.project_name
      CORS_ORIGIN               = "*"
    }
  }

  depends_on = [
    null_resource.token_generator_dependencies,
    data.archive_file.token_generator_zip
  ]

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
    Purpose  = "TokenGenerator"
  })
}

# -----------------------------------------------------------------------------
# Scheduling
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "ingestion_schedule" {
  name                = "${var.project_name}-ingestion-schedule"
  description         = "Trigger data ingestion every 5 minutes during trading hours"
  schedule_expression = "cron(0/5 3-10 ? * MON-FRI *)"

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
  })
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.ingestion_schedule.name
  target_id = "LambdaTarget"
  arn       = aws_lambda_function.data_ingestion.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_ingestion.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion_schedule.arn
}

# ETL Lambda scheduled to run once daily at 4 PM IST (10:30 AM UTC)
# Processes previous day's data after market close
resource "aws_cloudwatch_event_rule" "etl_schedule" {
  name                = "${var.project_name}-etl-schedule"
  description         = "Trigger ETL processing daily after market close"
  schedule_expression = "cron(30 10 ? * MON-FRI *)"

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
    Purpose  = "ETL"
  })
}

resource "aws_cloudwatch_event_target" "etl_target" {
  rule      = aws_cloudwatch_event_rule.etl_schedule.name
  target_id = "ETLLambdaTarget"
  arn       = aws_lambda_function.lightweight_etl.arn
}

resource "aws_lambda_permission" "allow_eventbridge_etl" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lightweight_etl.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.etl_schedule.arn
}

# -----------------------------------------------------------------------------
# Token Generator API Gateway
# -----------------------------------------------------------------------------
resource "aws_api_gateway_rest_api" "token_generator" {
  name        = "${var.project_name}-token-generator"
  description = "API for Fyers Token Generator Web UI"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(local.common_tags, {
    FreeTier = "Yes"
    Purpose  = "TokenGenerator"
  })
}

resource "aws_api_gateway_method" "token_generator_options" {
  rest_api_id   = aws_api_gateway_rest_api.token_generator.id
  resource_id   = aws_api_gateway_rest_api.token_generator.root_resource_id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "token_generator_options" {
  rest_api_id = aws_api_gateway_rest_api.token_generator.id
  resource_id = aws_api_gateway_rest_api.token_generator.root_resource_id
  http_method = aws_api_gateway_method.token_generator_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "token_generator_options" {
  rest_api_id = aws_api_gateway_rest_api.token_generator.id
  resource_id = aws_api_gateway_rest_api.token_generator.root_resource_id
  http_method = aws_api_gateway_method.token_generator_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "token_generator_options" {
  rest_api_id = aws_api_gateway_rest_api.token_generator.id
  resource_id = aws_api_gateway_rest_api.token_generator.root_resource_id
  http_method = aws_api_gateway_method.token_generator_options.http_method
  status_code = aws_api_gateway_method_response.token_generator_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_method" "token_generator_get" {
  rest_api_id   = aws_api_gateway_rest_api.token_generator.id
  resource_id   = aws_api_gateway_rest_api.token_generator.root_resource_id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "token_generator_post" {
  rest_api_id   = aws_api_gateway_rest_api.token_generator.id
  resource_id   = aws_api_gateway_rest_api.token_generator.root_resource_id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "token_generator_get" {
  rest_api_id             = aws_api_gateway_rest_api.token_generator.id
  resource_id             = aws_api_gateway_rest_api.token_generator.root_resource_id
  http_method             = aws_api_gateway_method.token_generator_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.token_generator.invoke_arn
}

resource "aws_api_gateway_integration" "token_generator_post" {
  rest_api_id             = aws_api_gateway_rest_api.token_generator.id
  resource_id             = aws_api_gateway_rest_api.token_generator.root_resource_id
  http_method             = aws_api_gateway_method.token_generator_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.token_generator.invoke_arn
}

resource "aws_lambda_permission" "token_generator_api" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.token_generator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.token_generator.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "token_generator" {
  depends_on = [
    aws_api_gateway_integration.token_generator_get,
    aws_api_gateway_integration.token_generator_post,
    aws_api_gateway_integration.token_generator_options
  ]

  rest_api_id = aws_api_gateway_rest_api.token_generator.id
  # `stage_name` is deprecated; stage is managed separately via
  # aws_api_gateway_stage.token_generator.
  lifecycle {
    create_before_destroy = true
  }
}

# Explicit stage resource for the token generator API. Managing the stage as a
# separate resource avoids the provider deprecation warning and gives us a
# stable place to attach stage-level settings in future.
resource "aws_api_gateway_stage" "token_generator" {
  deployment_id = aws_api_gateway_deployment.token_generator.id
  rest_api_id   = aws_api_gateway_rest_api.token_generator.id
  stage_name    = "prod"

  tags = merge(local.common_tags, {
    Stage = "prod"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# -----------------------------------------------------------------------------
# Analytics Lambda (Pandas-based queries - 100% FREE)
# COMMENTED OUT: Pandas package too large for Mumbai region (no Lambda Layers)
# Use lightweight_etl.py or query CSV files directly via S3 Select
# -----------------------------------------------------------------------------
# resource "aws_lambda_function" "analytics" {
#   s3_bucket        = aws_s3_bucket.ohlcv_data.id
#   s3_key           = "lambda/lambda_analytics.zip"
#   function_name    = "${var.project_name}-${var.environment}-analytics"
#   role             = aws_iam_role.lambda_execution.arn
#   handler          = "lambda_analytics.lambda_handler"
#   source_code_hash = filebase64sha256("${path.module}/../deployment/lambda_analytics.zip")
#   runtime          = "python3.11"
#   timeout          = 60
#   memory_size      = 1536  # 1.5 GB for Pandas operations
# 
#   environment {
#     variables = {
#       S3_BUCKET_NAME = aws_s3_bucket.ohlcv_data.id
#       CSV_PREFIX     = "analytics/csv"
#     }
#   }
# 
#   tags = merge(local.common_tags, {
#     Purpose  = "DataAnalytics"
#     FreeTier = "Yes"
#   })
# }
# 
# resource "aws_cloudwatch_log_group" "analytics_logs" {
#   name              = "/aws/lambda/${aws_lambda_function.analytics.function_name}"
#   retention_in_days = 7
# 
#   tags = merge(local.common_tags, {
#     Purpose = "Logging"
#   })
# }

# -----------------------------------------------------------------------------
# IAM
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "${var.project_name}-lambda-permissions"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.ohlcv_data.arn,
          "${aws_s3_bucket.ohlcv_data.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:PutParameter"]
        Resource = [
          aws_ssm_parameter.fyers_access_token.arn,
          aws_ssm_parameter.fyers_refresh_token.arn,
          aws_ssm_parameter.fyers_client_id.arn,
          aws_ssm_parameter.fyers_app_secret.arn,
          aws_ssm_parameter.fyers_pin.arn
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = [aws_sns_topic.alerts.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Cost Guardrail
# -----------------------------------------------------------------------------
resource "aws_budgets_budget" "mvp_budget" {
  name         = "${var.project_name}-mvp-budget"
  budget_type  = "COST"
  limit_amount = "5"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  time_period_start = "2025-01-01_00:00"

  cost_filter {
    name   = "Service"
    values = [
      "Amazon Simple Storage Service",
      "AWS Lambda",
      "Amazon Simple Notification Service",
      "AWS Systems Manager"
    ]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.notification_email]
  }

  tags = merge(local.common_tags, {
    Purpose = "CostControl"
    Budget  = "MVP"
  })
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "s3_bucket_name" {
  description = "Name of the S3 bucket for OHLCV data"
  value       = aws_s3_bucket.ohlcv_data.id
}

output "lambda_function_name" {
  description = "Lambda function name for data ingestion"
  value       = aws_lambda_function.data_ingestion.function_name
}

output "etl_lambda_function_name" {
  description = "Lambda function name for ETL processing"
  value       = aws_lambda_function.lightweight_etl.function_name
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "fyers_parameter_prefix" {
  description = "Fyers API credentials SSM parameter prefix"
  value       = "/${var.project_name}/fyers/"
}

output "fyers_access_token_param" {
  description = "Fyers access token SSM parameter name"
  value       = aws_ssm_parameter.fyers_access_token.name
}

output "fyers_refresh_token_param" {
  description = "Fyers refresh token SSM parameter name"
  value       = aws_ssm_parameter.fyers_refresh_token.name
}

output "fyers_client_id_param" {
  description = "Fyers client ID SSM parameter name"
  value       = aws_ssm_parameter.fyers_client_id.name
}

output "fyers_app_secret_param" {
  description = "Fyers app secret SSM parameter name"
  value       = aws_ssm_parameter.fyers_app_secret.name
}

output "fyers_pin_param" {
  description = "Fyers PIN SSM parameter name (optional)"
  value       = aws_ssm_parameter.fyers_pin.name
}

output "token_generator_url" {
  description = "AWS-hosted Token Generator Web UI URL"
  value       = "https://${aws_api_gateway_rest_api.token_generator.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod"
}

output "cloudwatch_logs_url" {
  description = "CloudWatch logs URL for monitoring Lambda function"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups/log-group/${replace(aws_cloudwatch_log_group.lambda_logs.name, "/", "$252F")}"
}

output "etl_cloudwatch_logs_url" {
  description = "CloudWatch logs URL for monitoring ETL Lambda function"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups/log-group/${replace(aws_cloudwatch_log_group.etl_logs.name, "/", "$252F")}"
}

output "s3_console_url" {
  description = "S3 console URL for viewing stored data"
  value       = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.ohlcv_data.id}?region=${data.aws_region.current.name}"
}

output "s3_analytics_path" {
  description = "S3 path for analytics CSV files"
  value       = "s3://${aws_s3_bucket.ohlcv_data.id}/analytics/csv/"
}

output "mvp_budget_name" {
  description = "MVP cost budget name"
  value       = aws_budgets_budget.mvp_budget.name
}

# output "analytics_lambda_function_name" {
#   description = "Lambda function name for analytics queries (Pandas-based)"
#   value       = aws_lambda_function.analytics.function_name
# }

output "deployment_summary" {
  description = "Deployment summary with key information"
  value = {
    ingestion_lambda    = aws_lambda_function.data_ingestion.function_name
    etl_lambda          = aws_lambda_function.lightweight_etl.function_name
    # analytics_lambda    = aws_lambda_function.analytics.function_name  # Commented out - Pandas too large for Mumbai
    s3_bucket           = aws_s3_bucket.ohlcv_data.id
    raw_data_path       = "s3://${aws_s3_bucket.ohlcv_data.id}/Raw data/Prices/"
    analytics_csv_path  = "s3://${aws_s3_bucket.ohlcv_data.id}/analytics/csv/"
    ingestion_schedule  = "Every 5 minutes during trading hours (Mon-Fri 9:15-15:30 IST)"
    etl_schedule        = "Daily at 4:00 PM IST (10:30 AM UTC)"
    analytics_info      = "Query CSV files directly from S3 or use Athena (see FREE_TIER_ALTERNATIVES.md)"
    token_generator_ui  = "https://${aws_api_gateway_rest_api.token_generator.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/prod"
  }
}