# API Gateway infrastructure for serving stock data to other teams
# This creates production-ready REST endpoints for data consumption

#===============================================================================
# API GATEWAY FOR DATA SERVING
#===============================================================================

# REST API Gateway (Free: 1M API calls per month)
resource "aws_api_gateway_rest_api" "stock_data_api" {
  name        = "${var.project_name}-stock-data-api"
  description = "REST API for serving stock OHLCV data to other teams"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(local.common_tags, {
    Purpose  = "DataServing"
    FreeTier = "Yes"
  })
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "stock_data_api" {
  depends_on = [
    aws_api_gateway_method.get_symbols,
    aws_api_gateway_method.get_ohlcv,
    aws_api_gateway_method.get_latest,
    aws_api_gateway_method.get_historical
  ]

  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  # `stage_name` is deprecated in the provider. Deployment targets are managed
  # via a separate aws_api_gateway_stage resource. Keep the variables metadata
  # but do not set a stage_name here to avoid the deprecation warning and
  # potential unexpected behavior during replacement.
  variables = {
    "deployed_at" = timestamp()
  }

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "stock_data_api" {
  deployment_id = aws_api_gateway_deployment.stock_data_api.id
  rest_api_id   = aws_api_gateway_rest_api.stock_data_api.id
  stage_name    = var.environment

  tags = merge(local.common_tags, {
    Stage = var.environment
  })
}

#===============================================================================
# API RESOURCES & METHODS
#===============================================================================

# /symbols endpoint
resource "aws_api_gateway_resource" "symbols" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  parent_id   = aws_api_gateway_rest_api.stock_data_api.root_resource_id
  path_part   = "symbols"
}

resource "aws_api_gateway_method" "get_symbols" {
  rest_api_id   = aws_api_gateway_rest_api.stock_data_api.id
  resource_id   = aws_api_gateway_resource.symbols.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.querystring.limit" = false
  }
}

resource "aws_api_gateway_integration" "get_symbols" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  resource_id = aws_api_gateway_resource.symbols.id
  http_method = aws_api_gateway_method.get_symbols.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

# /ohlcv/{symbol} endpoint
resource "aws_api_gateway_resource" "ohlcv" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  parent_id   = aws_api_gateway_rest_api.stock_data_api.root_resource_id
  path_part   = "ohlcv"
}

resource "aws_api_gateway_resource" "ohlcv_symbol" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  parent_id   = aws_api_gateway_resource.ohlcv.id
  path_part   = "{symbol}"
}

resource "aws_api_gateway_method" "get_ohlcv" {
  rest_api_id   = aws_api_gateway_rest_api.stock_data_api.id
  resource_id   = aws_api_gateway_resource.ohlcv_symbol.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.symbol"          = true
    "method.request.querystring.from"     = false
    "method.request.querystring.to"       = false
    "method.request.querystring.interval" = false
    "method.request.querystring.limit"    = false
  }
}

resource "aws_api_gateway_integration" "get_ohlcv" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  resource_id = aws_api_gateway_resource.ohlcv_symbol.id
  http_method = aws_api_gateway_method.get_ohlcv.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

# /latest endpoint (latest data for all symbols)
resource "aws_api_gateway_resource" "latest" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  parent_id   = aws_api_gateway_rest_api.stock_data_api.root_resource_id
  path_part   = "latest"
}

resource "aws_api_gateway_method" "get_latest" {
  rest_api_id   = aws_api_gateway_rest_api.stock_data_api.id
  resource_id   = aws_api_gateway_resource.latest.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.querystring.symbols" = false
  }
}

resource "aws_api_gateway_integration" "get_latest" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  resource_id = aws_api_gateway_resource.latest.id
  http_method = aws_api_gateway_method.get_latest.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

# /historical endpoint (bulk historical data)
resource "aws_api_gateway_resource" "historical" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  parent_id   = aws_api_gateway_rest_api.stock_data_api.root_resource_id
  path_part   = "historical"
}

resource "aws_api_gateway_method" "get_historical" {
  rest_api_id   = aws_api_gateway_rest_api.stock_data_api.id
  resource_id   = aws_api_gateway_resource.historical.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.querystring.symbol"   = false
    "method.request.querystring.symbols"  = false
    "method.request.querystring.from"     = false
    "method.request.querystring.to"       = false
    "method.request.querystring.interval" = false
    "method.request.querystring.format"   = false
  }
}

resource "aws_api_gateway_integration" "get_historical" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  resource_id = aws_api_gateway_resource.historical.id
  http_method = aws_api_gateway_method.get_historical.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

#===============================================================================
# CORS CONFIGURATION
#===============================================================================

# Enable CORS for all endpoints
resource "aws_api_gateway_method" "options_symbols" {
  rest_api_id   = aws_api_gateway_rest_api.stock_data_api.id
  resource_id   = aws_api_gateway_resource.symbols.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_symbols" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  resource_id = aws_api_gateway_resource.symbols.id
  http_method = aws_api_gateway_method.options_symbols.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "options_symbols" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  resource_id = aws_api_gateway_resource.symbols.id
  http_method = aws_api_gateway_method.options_symbols.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_symbols" {
  rest_api_id = aws_api_gateway_rest_api.stock_data_api.id
  resource_id = aws_api_gateway_resource.symbols.id
  http_method = aws_api_gateway_method.options_symbols.http_method
  status_code = aws_api_gateway_method_response.options_symbols.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

#===============================================================================
# CLOUDWATCH LOGS FOR API LAMBDA
#===============================================================================

resource "aws_cloudwatch_log_group" "api_lambda" {
  name              = "/aws/lambda/${var.project_name}-api-handler"
  retention_in_days = 14

  tags = merge(local.common_tags, {
    Purpose  = "APILogs"
    FreeTier = "Yes"
  })
}

#===============================================================================
# LAMBDA FUNCTION FOR API HANDLING
#===============================================================================

resource "aws_lambda_function" "api_handler" {
  filename         = "../deployment/api_handler.zip"
  function_name    = "${var.project_name}-api-handler"
  role            = aws_iam_role.api_lambda_execution.arn
  handler         = "api_handler.lambda_handler"
  source_code_hash = data.archive_file.api_lambda_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 30

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.ohlcv_data.id
      PROJECT_NAME   = var.project_name
      ENVIRONMENT    = var.environment
    }
  }

  depends_on = [
    null_resource.api_lambda_dependencies,
    data.archive_file.api_lambda_zip
  ]

  tags = merge(local.common_tags, {
    Purpose  = "APIServing"
    FreeTier = "Yes"
  })
}

# Package API Lambda function
data "archive_file" "api_lambda_zip" {
  type        = "zip"
  output_path = "../deployment/api_handler.zip"
  source_dir  = "../deployment/api_package"
  
  depends_on = [null_resource.api_lambda_dependencies]
}

resource "null_resource" "api_lambda_dependencies" {
  triggers = {
    api_code = filemd5("../api/api_handler.py")
  }

  provisioner "local-exec" {
    command = <<-EOT
      if (Test-Path "../deployment/api_package") { Remove-Item "../deployment/api_package" -Recurse -Force }
      New-Item -ItemType Directory -Path "../deployment/api_package" -Force
      Copy-Item "../api/api_handler.py" "../deployment/api_package/"
      pip install boto3 -t "../deployment/api_package" --quiet
      if (Test-Path "../deployment/api_handler.zip") { Remove-Item "../deployment/api_handler.zip" -Force }
      Compress-Archive -Path "../deployment/api_package/*" -DestinationPath "../deployment/api_handler.zip"
    EOT
    
    interpreter = ["powershell", "-Command"]
    working_dir = path.module
  }
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.stock_data_api.execution_arn}/*/*"
}

# IAM Role for API Lambda
resource "aws_iam_role" "api_lambda_execution" {
  name = "${var.project_name}-api-lambda-execution-role"

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

resource "aws_iam_role_policy_attachment" "api_lambda_basic" {
  role       = aws_iam_role.api_lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "api_lambda_permissions" {
  name = "${var.project_name}-api-lambda-permissions"
  role = aws_iam_role.api_lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.ohlcv_data.arn,
          "${aws_s3_bucket.ohlcv_data.arn}/*"
        ]
      }
    ]
  })
}

#===============================================================================
# OUTPUTS
#===============================================================================

output "api_gateway_url" {
  description = "API Gateway endpoint URL for other teams"
  value       = "https://${aws_api_gateway_rest_api.stock_data_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.environment}"
}

output "api_endpoints" {
  description = "Available API endpoints for other teams"
  value = {
    "symbols"     = "GET /symbols - List all available symbols"
    "ohlcv"       = "GET /ohlcv/{symbol}?from=YYYY-MM-DD&to=YYYY-MM-DD&interval=5 - Get OHLCV data for specific symbol"
    "latest"      = "GET /latest?symbols=SYMBOL1,SYMBOL2 - Get latest data for symbols"
    "historical"  = "GET /historical?symbol=SYMBOL&from=YYYY-MM-DD&to=YYYY-MM-DD - Get historical data"
  }
}
