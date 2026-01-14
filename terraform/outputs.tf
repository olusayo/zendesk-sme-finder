# Consolidated Outputs File

# API Gateway Outputs
output "api_gateway_endpoint" {
  description = "Full API Gateway endpoint URL for finding FDEs"
  value       = "${aws_api_gateway_stage.production.invoke_url}/find-fdes"
}

output "api_gateway_stage_name" {
  description = "API Gateway stage name"
  value       = aws_api_gateway_stage.production.stage_name
}

output "api_key" {
  description = "API Gateway key value (use for x-api-key header)"
  value       = aws_api_gateway_api_key.main.value
  sensitive   = true
}

# Lambda Function Outputs
output "lambda_functions" {
  description = "Lambda function details"
  value = {
    zendesk_actions = {
      arn           = aws_lambda_function.zendesk_actions.arn
      function_name = aws_lambda_function.zendesk_actions.function_name
    }
    slack_actions = {
      arn           = aws_lambda_function.slack_actions.arn
      function_name = aws_lambda_function.slack_actions.function_name
    }
    orchestration = {
      arn           = aws_lambda_function.orchestration.arn
      function_name = aws_lambda_function.orchestration.function_name
    }
  }
}

# IAM Role Outputs
output "iam_roles" {
  description = "IAM role ARNs"
  value = {
    lambda_execution_role = aws_iam_role.lambda_execution_role.arn
    bedrock_agent_role    = aws_iam_role.bedrock_agent_role.arn
  }
}

# Secrets Manager Outputs
output "secrets" {
  description = "Secrets Manager secret names"
  value = {
    zendesk_credentials = aws_secretsmanager_secret.zendesk_credentials.name
    slack_credentials   = aws_secretsmanager_secret.slack_credentials.name
  }
}

# CloudWatch Log Groups
output "cloudwatch_log_groups" {
  description = "CloudWatch Log Group names"
  value = {
    zendesk_actions = aws_cloudwatch_log_group.zendesk_actions.name
    slack_actions   = aws_cloudwatch_log_group.slack_actions.name
    orchestration   = aws_cloudwatch_log_group.orchestration.name
    api_gateway     = aws_cloudwatch_log_group.api_gateway.name
  }
}

# Configuration for Frontend
output "frontend_config" {
  description = "Configuration values for the Streamlit frontend"
  value = {
    api_endpoint = "${aws_api_gateway_stage.production.invoke_url}/find-fdes"
    api_key      = aws_api_gateway_api_key.main.value
  }
  sensitive = true
}

# Bedrock Resources Outputs
output "bedrock_resources" {
  description = "Bedrock Agent and Knowledge Base details"
  value = var.enable_bedrock_agent ? {
    agent_id              = aws_bedrockagent_agent.fde_finder[0].id
    agent_arn             = aws_bedrockagent_agent.fde_finder[0].agent_arn
    test_alias_id         = aws_bedrockagent_agent_alias.test[0].agent_alias_id
    production_alias_id   = aws_bedrockagent_agent_alias.production[0].agent_alias_id
    tickets_kb_id         = var.enable_knowledge_bases ? aws_bedrockagent_knowledge_base.tickets[0].id : null
    fde_profiles_kb_id    = var.enable_knowledge_bases ? aws_bedrockagent_knowledge_base.fde_profiles[0].id : null
    tickets_data_source   = var.enable_knowledge_bases ? aws_bedrockagent_data_source.tickets[0].data_source_id : null
    fde_profiles_data_source = var.enable_knowledge_bases ? aws_bedrockagent_data_source.fde_profiles[0].data_source_id : null
  } : null
}

# S3 Data Bucket Outputs
output "s3_data_bucket" {
  description = "S3 bucket for Knowledge Base data"
  value = {
    bucket_name        = aws_s3_bucket.knowledge_base_data.id
    bucket_arn         = aws_s3_bucket.knowledge_base_data.arn
    tickets_path       = "s3://${aws_s3_bucket.knowledge_base_data.id}/tickets/"
    fde_profiles_path  = "s3://${aws_s3_bucket.knowledge_base_data.id}/fde-profiles/"
  }
}

# Post-Deployment Instructions
output "post_deployment_instructions" {
  description = "Next steps after Terraform deployment"
  value       = <<-EOT

  ========================================
  ✅ Terraform Deployment Completed!
  ========================================

  🎉 FULLY AUTOMATED INFRASTRUCTURE DEPLOYED:
  ${var.enable_bedrock_agent ? "  ✅ Bedrock Agent created automatically" : "  ⚠️  Bedrock Agent creation disabled"}
  ${var.enable_knowledge_bases ? "  ✅ Knowledge Bases created automatically" : "  ⚠️  Knowledge Base creation disabled"}
  ✅ Lambda Function URL created (15-minute timeout support)
  ✅ S3 bucket for Knowledge Base data
  ✅ OpenSearch Serverless collections
  ✅ ECS Fargate frontend
  ✅ All IAM roles and policies

  📋 NEXT STEPS:

  1. UPLOAD DATA TO KNOWLEDGE BASES:
     Upload your CSV files to S3:
     - Tickets: s3://${aws_s3_bucket.knowledge_base_data.id}/tickets/
     - FDE Profiles: s3://${aws_s3_bucket.knowledge_base_data.id}/fde-profiles/

     Then trigger ingestion (after creating Knowledge Bases manually):
     ${var.enable_knowledge_bases ? "aws bedrock-agent start-ingestion-job --knowledge-base-id ${aws_bedrockagent_knowledge_base.tickets[0].id} --data-source-id ${aws_bedrockagent_data_source.tickets[0].data_source_id}" : "# Knowledge Bases need to be created manually - see COMPLETE_DEPLOYMENT_GUIDE.md Part 7"}

  2. ACCESS YOUR FRONTEND:
     Streamlit App URL: http://${aws_lb.frontend.dns_name}

  3. LAMBDA FUNCTION URL (Direct Access):
     ${aws_lambda_function_url.orchestration.function_url}

     Test with:
     curl -X POST "${aws_lambda_function_url.orchestration.function_url}" \
       -H "Content-Type: application/json" \
       -d '{"ticket_description": "PostgreSQL performance issues"}'

  4. VIEW ALL OUTPUTS:
     terraform output -json | jq

  5. CHECK CLOUDWATCH LOGS:
     - ${aws_cloudwatch_log_group.orchestration.name}
     ${var.enable_bedrock_agent ? "- Bedrock Agent: /aws/bedrock/agents/${aws_bedrockagent_agent.fde_finder[0].id}" : ""}

  For detailed instructions, see terraform/TERRAFORM_DEPLOYMENT_GUIDE.md

  ========================================
  EOT
}

# ECS and Frontend Outputs
output "frontend_url" {
  description = "URL of the Streamlit frontend (ALB DNS)"
  value       = "http://${aws_lb.frontend.dns_name}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for frontend Docker images"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.frontend.name
}

# Summary Output
output "deployment_summary" {
  description = "Deployment summary"
  value = {
    region       = data.aws_region.current.name
    account_id   = data.aws_caller_identity.current.account_id
    project_name = var.project_name
    environment  = var.environment
    api_endpoint = "${aws_api_gateway_stage.production.invoke_url}/find-fdes"
    frontend_url = "http://${aws_lb.frontend.dns_name}"
    lambda_functions = [
      aws_lambda_function.zendesk_actions.function_name,
      aws_lambda_function.slack_actions.function_name,
      aws_lambda_function.orchestration.function_name
    ]
  }
}
