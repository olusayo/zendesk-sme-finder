# REST API Gateway
resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-api"
  description = "API Gateway for Zendesk SME Finder"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-api"
    }
  )
}

# API Gateway Resource (/find-fdes)
resource "aws_api_gateway_resource" "find_fdes" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "find-fdes"
}

# POST Method for /find-fdes
resource "aws_api_gateway_method" "find_fdes_post" {
  rest_api_id      = aws_api_gateway_rest_api.main.id
  resource_id      = aws_api_gateway_resource.find_fdes.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

# Lambda Integration
resource "aws_api_gateway_integration" "find_fdes_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.find_fdes.id
  http_method             = aws_api_gateway_method.find_fdes_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.orchestration.invoke_arn
}

# CORS Configuration - OPTIONS Method
resource "aws_api_gateway_method" "find_fdes_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.find_fdes.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "find_fdes_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.find_fdes.id
  http_method = aws_api_gateway_method.find_fdes_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "find_fdes_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.find_fdes.id
  http_method = aws_api_gateway_method.find_fdes_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "find_fdes_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.find_fdes.id
  http_method = aws_api_gateway_method.find_fdes_options.http_method
  status_code = aws_api_gateway_method_response.find_fdes_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.find_fdes_options]
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.find_fdes.id,
      aws_api_gateway_method.find_fdes_post.id,
      aws_api_gateway_integration.find_fdes_lambda.id,
      aws_api_gateway_method.find_fdes_options.id,
      aws_api_gateway_integration.find_fdes_options.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.find_fdes_lambda,
    aws_api_gateway_integration.find_fdes_options
  ]
}

# API Gateway Stage
resource "aws_api_gateway_stage" "production" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-${var.environment}-stage"
    }
  )
}

# API Key
resource "aws_api_gateway_api_key" "main" {
  name    = "${var.project_name}-api-key"
  enabled = true

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-api-key"
    }
  )
}

# Usage Plan
resource "aws_api_gateway_usage_plan" "main" {
  name        = "${var.project_name}-usage-plan"
  description = "Usage plan for Zendesk SME Finder API"

  api_stages {
    api_id = aws_api_gateway_rest_api.main.id
    stage  = aws_api_gateway_stage.production.stage_name
  }

  throttle_settings {
    rate_limit  = var.api_throttle_rate_limit
    burst_limit = var.api_throttle_burst_limit
  }

  quota_settings {
    limit  = var.api_quota_limit
    period = "MONTH"
  }

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-usage-plan"
    }
  )
}

# Associate API Key with Usage Plan
resource "aws_api_gateway_usage_plan_key" "main" {
  key_id        = aws_api_gateway_api_key.main.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.main.id
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}"
  retention_in_days = 7

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-api-logs"
    }
  )
}

# Outputs
output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_stage.production.invoke_url}/find-fdes"
}

output "api_key_id" {
  description = "API Gateway key ID"
  value       = aws_api_gateway_api_key.main.id
}

output "api_key_value" {
  description = "API Gateway key value"
  value       = aws_api_gateway_api_key.main.value
  sensitive   = true
}
