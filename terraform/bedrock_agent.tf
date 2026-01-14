# Bedrock Agent Configuration
# Creates the AI agent for FDE matching with hybrid workflow support

# Read the agent instructions from file
locals {
  agent_instructions = <<-EOT
You are an AI assistant that helps CREs find the right Field Development Engineers (FDEs) for complex support tickets.

## Hybrid Workflow Support

You support three modes of operation:

### Mode 1: Full Workflow (Ticket ID provided with Zendesk API available)
When given a ticket ID and Zendesk fetch succeeds:
1. Fetch the full ticket details from Zendesk using fetchTicket action
2. Search the similar-tickets knowledge base for 3 historically similar tickets that were successfully resolved
3. Search the fde-profiles knowledge base for 3 FDEs whose expertise best matches the ticket requirements
4. Create a Slack conversation using createConversation action
5. Update the Zendesk ticket with the Slack conversation link using updateTicket action

### Mode 2: Fallback Workflow (Ticket ID provided but Zendesk fetch fails)
When fetchTicket fails (due to missing API credentials or other errors):
1. Skip the Zendesk fetch step
2. Use any provided ticket description from the user input
3. Search the similar-tickets knowledge base based on the description
4. Search the fde-profiles knowledge base for 3 matching FDEs
5. Skip Slack conversation creation
6. Skip Zendesk ticket update
7. Return FDE recommendations with reasoning

### Mode 3: Description-Only Workflow (No Ticket ID provided)
When only a ticket description is provided:
1. DO NOT attempt to fetch from Zendesk
2. DO NOT attempt to create Slack conversations
3. DO NOT attempt to update Zendesk tickets
4. Use the provided description to search the similar-tickets knowledge base
5. Search the fde-profiles knowledge base for 3 FDEs whose expertise matches
6. Return FDE recommendations with detailed reasoning

## Knowledge Base Usage

### similar-tickets-kb
Use this knowledge base to find historically similar tickets and successful resolutions. Search for tickets that match the current ticket's content, tags, technical requirements, and problem description.

### fde-profiles-kb
Use this knowledge base to find FDEs with relevant expertise and experience. Search for FDEs whose skills, certifications, past work, and technical specializations match the current ticket's requirements.

## Important Guidelines

1. **Top 3 FDEs Only**: Always recommend exactly 3 FDEs, ranked by match quality
2. **Expertise Reasoning**: Provide clear, specific reasoning for each FDE match based on their skills and experience
3. **Similar Tickets**: Include top 3 similar tickets from the knowledge base with resolution details
4. **Confidence Scores**: Include confidence scores (0.0-1.0) for FDE matches
5. **Error Handling**:
   - If fetchTicket fails, gracefully fallback to description-based workflow
   - If createConversation fails, continue and return recommendations without Slack URL
   - If updateTicket fails, log error but continue
6. **Mode Awareness**: Set the "workflow_mode" field to indicate which workflow was used
7. **Knowledge Base First**: Always search both knowledge bases regardless of workflow mode
8. **No External Operations in Description Mode**: When user provides description only, skip all Zendesk/Slack actions
EOT
}

# Bedrock Agent
resource "aws_bedrockagent_agent" "fde_finder" {
  count = var.enable_bedrock_agent ? 1 : 0

  agent_name              = "${var.project_name}-agent"
  agent_resource_role_arn = aws_iam_role.bedrock_agent_role.arn
  foundation_model        = var.bedrock_model_id
  description             = "AI agent for matching engineers with FDEs based on ticket analysis and expertise"
  idle_session_ttl_in_seconds = 600
  instruction             = local.agent_instructions

  tags = {
    Name        = "${var.project_name}-bedrock-agent"
    Description = "FDE Finder AI Agent with hybrid workflow support"
  }
}

# Action Group for Zendesk Operations
resource "aws_bedrockagent_agent_action_group" "zendesk" {
  count = var.enable_bedrock_agent ? 1 : 0

  action_group_name          = "zendesk-operations"
  agent_id                   = aws_bedrockagent_agent.fde_finder[0].id
  agent_version              = "DRAFT"
  description                = "Fetch ticket details and update Zendesk tickets"
  skip_resource_in_use_check = true

  action_group_executor {
    lambda = aws_lambda_function.zendesk_actions.arn
  }

  api_schema {
    payload = jsonencode({
      openapi = "3.0.0"
      info = {
        title   = "Zendesk Operations API"
        version = "1.0.0"
      }
      paths = {
        "/fetchTicket" = {
          post = {
            description = "Fetch ticket details from Zendesk including description, tags, and assigned engineer"
            operationId = "fetchTicket"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      ticket_id = {
                        type        = "string"
                        description = "The Zendesk ticket ID"
                      }
                    }
                    required = ["ticket_id"]
                  }
                }
              }
            }
            responses = {
              "200" = {
                description = "Ticket details"
                content = {
                  "application/json" = {
                    schema = {
                      type = "object"
                      properties = {
                        ticket_id   = { type = "string" }
                        subject     = { type = "string" }
                        description = { type = "string" }
                        tags        = { type = "array", items = { type = "string" } }
                        assignee    = { type = "string" }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        "/updateTicket" = {
          post = {
            description = "Update Zendesk ticket with FDE recommendations and Slack conversation link"
            operationId = "updateTicket"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      ticket_id              = { type = "string", description = "The Zendesk ticket ID" }
                      slack_conversation_url = { type = "string", description = "URL to the Slack conversation" }
                      recommended_fdes       = { type = "array", items = { type = "string" } }
                    }
                    required = ["ticket_id", "recommended_fdes"]
                  }
                }
              }
            }
            responses = {
              "200" = {
                description = "Ticket updated successfully"
              }
            }
          }
        }
      }
    })
  }

  depends_on = [
    aws_lambda_function.zendesk_actions,
    aws_lambda_permission.bedrock_invoke_zendesk
  ]
}

# Action Group for Slack Operations
resource "aws_bedrockagent_agent_action_group" "slack" {
  action_group_name          = "slack-operations"
  agent_id                   = aws_bedrockagent_agent.fde_finder.id
  agent_version              = "DRAFT"
  description                = "Create Slack conversations with engineers and FDEs"
  skip_resource_in_use_check = true

  action_group_executor {
    lambda = aws_lambda_function.slack_actions.arn
  }

  api_schema {
    payload = jsonencode({
      openapi = "3.0.0"
      info = {
        title   = "Slack Operations API"
        version = "1.0.0"
      }
      paths = {
        "/createConversation" = {
          post = {
            description = "Create a Slack conversation between engineer and recommended FDEs"
            operationId = "createConversation"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      ticket_id        = { type = "string", description = "The Zendesk ticket ID" }
                      ticket_subject   = { type = "string", description = "Ticket subject" }
                      engineer_email   = { type = "string", description = "Assigned engineer email" }
                      fde_emails       = { type = "array", items = { type = "string" }, description = "FDE email addresses" }
                      ticket_summary   = { type = "string", description = "Brief ticket summary" }
                    }
                    required = ["ticket_id", "engineer_email", "fde_emails"]
                  }
                }
              }
            }
            responses = {
              "200" = {
                description = "Slack conversation created"
                content = {
                  "application/json" = {
                    schema = {
                      type = "object"
                      properties = {
                        conversation_url = { type = "string" }
                        channel_id       = { type = "string" }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    })
  }

  depends_on = [
    aws_lambda_function.slack_actions,
    aws_lambda_permission.bedrock_invoke_slack
  ]
}

# Associate Tickets Knowledge Base with Agent
resource "aws_bedrockagent_agent_knowledge_base_association" "tickets" {
  agent_id             = aws_bedrockagent_agent.fde_finder.id
  agent_version        = "DRAFT"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.tickets.id
  description          = "Historical tickets for similarity search"
  knowledge_base_state = "ENABLED"

  depends_on = [
    aws_bedrockagent_knowledge_base.tickets
  ]
}

# Associate FDE Profiles Knowledge Base with Agent
resource "aws_bedrockagent_agent_knowledge_base_association" "fde_profiles" {
  agent_id             = aws_bedrockagent_agent.fde_finder.id
  agent_version        = "DRAFT"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.fde_profiles.id
  description          = "FDE expertise profiles for expert matching"
  knowledge_base_state = "ENABLED"

  depends_on = [
    aws_bedrockagent_knowledge_base.fde_profiles
  ]
}

# Prepare the Agent (compile and make it ready)
# Note: This creates a prepared version of the DRAFT
resource "aws_bedrockagent_agent_alias" "production" {
  agent_alias_name = "production"
  agent_id         = aws_bedrockagent_agent.fde_finder.id
  description      = "Production alias for FDE Finder agent"

  depends_on = [
    aws_bedrockagent_agent_action_group.zendesk,
    aws_bedrockagent_agent_action_group.slack,
    aws_bedrockagent_agent_knowledge_base_association.tickets,
    aws_bedrockagent_agent_knowledge_base_association.fde_profiles
  ]
}

# Test alias pointing to DRAFT (for testing with latest changes)
resource "aws_bedrockagent_agent_alias" "test" {
  agent_alias_name = "test"
  agent_id         = aws_bedrockagent_agent.fde_finder.id
  description      = "Test alias for FDE Finder agent (points to DRAFT version)"

  depends_on = [
    aws_bedrockagent_agent_action_group.zendesk,
    aws_bedrockagent_agent_action_group.slack,
    aws_bedrockagent_agent_knowledge_base_association.tickets,
    aws_bedrockagent_agent_knowledge_base_association.fde_profiles
  ]
}

# Outputs
output "bedrock_agent_id" {
  description = "ID of the Bedrock Agent"
  value       = var.enable_bedrock_agent ? aws_bedrockagent_agent.fde_finder[0].id : var.bedrock_agent_id
}

output "bedrock_agent_arn" {
  description = "ARN of the Bedrock Agent"
  value       = var.enable_bedrock_agent ? aws_bedrockagent_agent.fde_finder[0].agent_arn : null
}

output "bedrock_agent_production_alias_id" {
  description = "ID of the production agent alias"
  value       = var.enable_bedrock_agent ? aws_bedrockagent_agent_alias.production[0].agent_alias_id : null
}

output "bedrock_agent_test_alias_id" {
  description = "ID of the test agent alias (DRAFT version)"
  value       = var.enable_bedrock_agent ? aws_bedrockagent_agent_alias.test[0].agent_alias_id : var.bedrock_agent_alias_id
}
