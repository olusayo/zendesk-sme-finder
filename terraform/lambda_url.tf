# Lambda Function URL Configuration
# Provides direct HTTPS endpoint for Lambda with 15-minute timeout support

# Create Function URL for Orchestration Lambda
resource "aws_lambda_function_url" "orchestration" {
  function_name      = aws_lambda_function.orchestration.function_name
  authorization_type = "NONE" # Public access - consider using IAM for production

  cors {
    allow_credentials = true
    allow_origins     = ["*"] # Restrict this in production
    allow_methods     = ["POST"]
    allow_headers     = ["content-type", "x-api-key"]
    expose_headers    = ["content-type"]
    max_age           = 86400
  }
}

# Lambda permission for public access via Function URL
resource "aws_lambda_permission" "function_url_public_access" {
  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.orchestration.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

# Output the Function URL
output "lambda_function_url" {
  description = "HTTPS URL for invoking the Orchestration Lambda directly (15-minute timeout)"
  value       = aws_lambda_function_url.orchestration.function_url
}

output "lambda_function_url_instructions" {
  description = "Instructions for using the Lambda Function URL"
  value       = <<-EOT
    Lambda Function URL: ${aws_lambda_function_url.orchestration.function_url}

    Usage:
    curl -X POST "${aws_lambda_function_url.orchestration.function_url}" \
      -H "Content-Type: application/json" \
      -d '{"ticket_description": "Customer experiencing PostgreSQL performance issues"}'

    Benefits over API Gateway:
    - 15-minute timeout (vs 29-second API Gateway limit)
    - No additional API Gateway costs
    - Direct Lambda invocation
    - Supports long-running Bedrock Agent requests

    Update your Streamlit frontend with this URL:
    export API_ENDPOINT="${aws_lambda_function_url.orchestration.function_url}"
  EOT
}
