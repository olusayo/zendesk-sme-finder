# Data source to package Lambda functions
data "archive_file" "zendesk_actions" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/action-groups/zendesk"
  output_path = "${path.module}/builds/zendesk-actions.zip"
  excludes    = ["package", "*.zip", "__pycache__", "*.pyc"]
}

data "archive_file" "slack_actions" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/action-groups/slack"
  output_path = "${path.module}/builds/slack-actions.zip"
  excludes    = ["package", "*.zip", "__pycache__", "*.pyc"]
}

data "archive_file" "orchestration" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/orchestration"
  output_path = "${path.module}/builds/orchestration.zip"
  excludes    = ["package", "*.zip", "__pycache__", "*.pyc"]
}

# Lambda Layer for shared dependencies
resource "null_resource" "lambda_dependencies" {
  triggers = {
    requirements_zendesk = filemd5("${path.module}/../lambdas/action-groups/zendesk/requirements.txt")
    requirements_slack   = filemd5("${path.module}/../lambdas/action-groups/slack/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      mkdir -p ${path.module}/builds/python
      pip install -r ${path.module}/../lambdas/action-groups/zendesk/requirements.txt -t ${path.module}/builds/python/
      pip install -r ${path.module}/../lambdas/action-groups/slack/requirements.txt -t ${path.module}/builds/python/
    EOT
  }
}

data "archive_file" "lambda_layer" {
  type        = "zip"
  source_dir  = "${path.module}/builds/python"
  output_path = "${path.module}/builds/lambda-layer.zip"

  depends_on = [null_resource.lambda_dependencies]
}

resource "aws_lambda_layer_version" "dependencies" {
  filename            = data.archive_file.lambda_layer.output_path
  layer_name          = "${var.project_name}-dependencies"
  compatible_runtimes = [var.lambda_runtime]
  source_code_hash    = data.archive_file.lambda_layer.output_base64sha256

  depends_on = [null_resource.lambda_dependencies]
}

# Zendesk Actions Lambda Function
resource "aws_lambda_function" "zendesk_actions" {
  filename         = data.archive_file.zendesk_actions.output_path
  function_name    = "${var.project_name}-zendesk-actions"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.zendesk_actions.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      ZENDESK_SECRET_NAME = aws_secretsmanager_secret.zendesk_credentials.name
    }
  }

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-zendesk-actions"
    }
  )
}

# Slack Actions Lambda Function
resource "aws_lambda_function" "slack_actions" {
  filename         = data.archive_file.slack_actions.output_path
  function_name    = "${var.project_name}-slack-actions"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.slack_actions.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      SLACK_SECRET_NAME = aws_secretsmanager_secret.slack_credentials.name
    }
  }

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-slack-actions"
    }
  )
}

# Orchestration Lambda Function
resource "aws_lambda_function" "orchestration" {
  filename         = data.archive_file.orchestration.output_path
  function_name    = "${var.project_name}-orchestration"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.orchestration.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.orchestration_lambda_timeout
  memory_size      = var.orchestration_lambda_memory_size

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      BEDROCK_AGENT_ID       = var.enable_bedrock_agent ? aws_bedrockagent_agent.fde_finder[0].id : var.bedrock_agent_id
      BEDROCK_AGENT_ALIAS_ID = var.enable_bedrock_agent ? aws_bedrockagent_agent_alias.test[0].agent_alias_id : var.bedrock_agent_alias_id
    }
  }

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-orchestration"
    }
  )
}

# Lambda permissions for Bedrock Agent to invoke action group Lambdas
resource "aws_lambda_permission" "bedrock_invoke_zendesk" {
  statement_id   = "AllowBedrockAgentInvoke"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.zendesk_actions.function_name
  principal      = "bedrock.amazonaws.com"
  source_account = data.aws_caller_identity.current.account_id
}

resource "aws_lambda_permission" "bedrock_invoke_slack" {
  statement_id   = "AllowBedrockAgentInvoke"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.slack_actions.function_name
  principal      = "bedrock.amazonaws.com"
  source_account = data.aws_caller_identity.current.account_id
}

# Lambda permission for API Gateway to invoke orchestration Lambda
resource "aws_lambda_permission" "apigateway_invoke_orchestration" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.orchestration.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# CloudWatch Log Groups for Lambda functions
resource "aws_cloudwatch_log_group" "zendesk_actions" {
  name              = "/aws/lambda/${aws_lambda_function.zendesk_actions.function_name}"
  retention_in_days = 7

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-zendesk-actions-logs"
    }
  )
}

resource "aws_cloudwatch_log_group" "slack_actions" {
  name              = "/aws/lambda/${aws_lambda_function.slack_actions.function_name}"
  retention_in_days = 7

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-slack-actions-logs"
    }
  )
}

resource "aws_cloudwatch_log_group" "orchestration" {
  name              = "/aws/lambda/${aws_lambda_function.orchestration.function_name}"
  retention_in_days = 7

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-orchestration-logs"
    }
  )
}

# Outputs
output "zendesk_actions_lambda_arn" {
  description = "ARN of the Zendesk Actions Lambda function"
  value       = aws_lambda_function.zendesk_actions.arn
}

output "slack_actions_lambda_arn" {
  description = "ARN of the Slack Actions Lambda function"
  value       = aws_lambda_function.slack_actions.arn
}

output "orchestration_lambda_arn" {
  description = "ARN of the Orchestration Lambda function"
  value       = aws_lambda_function.orchestration.arn
}
