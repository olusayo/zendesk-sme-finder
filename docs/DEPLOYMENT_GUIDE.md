# Deployment Guide - Zendesk SME Finder

This guide walks through deploying the Zendesk SME Finder application to AWS using Bedrock Agents.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Knowledge Bases Setup](#knowledge-bases-setup)
4. [Action Groups Lambda Deployment](#action-groups-lambda-deployment)
5. [Bedrock Agent Configuration](#bedrock-agent-configuration)
6. [Orchestration Lambda Deployment](#orchestration-lambda-deployment)
7. [API Gateway Setup](#api-gateway-setup)
8. [Streamlit Frontend Deployment](#streamlit-frontend-deployment)
9. [Testing](#testing)
10. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

## Prerequisites

Before starting, ensure you have:

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Python 3.11 or later
- Node.js 18 or later (for Streamlit deployment)
- Zendesk account with API access
- Slack workspace with bot token
- Basic familiarity with AWS services

### Required AWS Permissions

Your IAM user/role needs permissions for:
- Bedrock (Agent creation, Knowledge Base management)
- Lambda (function creation and deployment)
- S3 (bucket creation for Knowledge Base data)
- OpenSearch Serverless (for vector storage)
- IAM (role creation for Lambda and Bedrock Agent)
- API Gateway (REST API creation)
- CloudWatch (logs and metrics)
- Secrets Manager (for storing credentials)

## AWS Account Setup

### 1. Enable Bedrock Model Access

Navigate to the Bedrock console and request access to:
- Claude 3.5 Sonnet (for the agent)
- Amazon Titan Embeddings v2 (for Knowledge Bases)

This may take a few minutes to be approved.

### 2. Store Credentials in Secrets Manager

Create secrets for Zendesk and Slack credentials:

```bash
# Zendesk credentials
aws secretsmanager create-secret \
  --name zendesk-sme-finder/zendesk-credentials \
  --secret-string '{
    "domain": "your-company.zendesk.com",
    "email": "your-email@company.com",
    "api_token": "your-zendesk-api-token"
  }'

# Slack credentials
aws secretsmanager create-secret \
  --name zendesk-sme-finder/slack-credentials \
  --secret-string '{
    "bot_token": "xoxb-your-slack-bot-token",
    "team_url": "https://your-workspace.slack.com/"
  }'
```

## Knowledge Bases Setup

### 1. Use Existing S3 Data Sources

The project uses existing S3 buckets with data:

**Existing Data Sources**:
- **Tickets**: `s3://genai-enablement-team3/tickets/` (ARN: `arn:aws:s3:::genai-enablement-team3/tickets/`)
- **Certificates/FDE Profiles**: `s3://genai-enablement-team3/certificates/` (ARN: `arn:aws:s3:::genai-enablement-team3/certificates/`)

**Note**: The sample data in this repository (`data/knowledge-bases/`) is for reference only. The actual Knowledge Bases will use the data from the `genai-enablement-team3` bucket.

If you need to upload additional sample data for testing:

```bash
# Upload sample tickets (optional)
aws s3 cp data/knowledge-bases/similar-tickets/sample-tickets.json \
  s3://genai-enablement-team3/tickets/sample-tickets.json

# Upload sample FDE profiles (optional)
aws s3 cp data/knowledge-bases/fde-profiles/sample-fdes.json \
  s3://genai-enablement-team3/certificates/sample-fdes.json
```

### 2. Create OpenSearch Serverless Collections

```bash
# Create collection for similar tickets
aws opensearchserverless create-collection \
  --name similar-tickets-vectors \
  --type VECTORSEARCH \
  --description "Vector storage for similar Zendesk tickets"

# Create collection for FDE profiles
aws opensearchserverless create-collection \
  --name fde-profiles-vectors \
  --type VECTORSEARCH \
  --description "Vector storage for FDE expertise profiles"
```

Note the collection endpoints - you'll need them for Knowledge Base creation.

### 3. Create Knowledge Bases in Bedrock

Navigate to Bedrock Console > Knowledge Bases > Create Knowledge Base

#### Similar Tickets Knowledge Base

1. Name: `similar-tickets-kb`
2. Description: `Historical Zendesk tickets with resolutions`
3. Embeddings model: Amazon Titan Embeddings v2
4. Vector database: Select the `similar-tickets-vectors` collection
5. Data source: **S3 bucket `s3://genai-enablement-team3/tickets/`**
6. Chunking strategy: Fixed-size chunking (300 tokens, 20% overlap)
7. Create and sync the Knowledge Base

#### FDE Profiles Knowledge Base

1. Name: `fde-profiles-kb`
2. Description: `FDE expertise profiles and experience (certificates)`
3. Embeddings model: Amazon Titan Embeddings v2
4. Vector database: Select the `fde-profiles-vectors` collection
5. Data source: **S3 bucket `s3://genai-enablement-team3/certificates/`**
6. Chunking strategy: Fixed-size chunking (300 tokens, 20% overlap)
7. Create and sync the Knowledge Base

**Important**: Ensure the Bedrock service role has read permissions to the `genai-enablement-team3` bucket.

Note the Knowledge Base IDs - you'll need them for the Bedrock Agent configuration.

## Action Groups Lambda Deployment

### 1. Create IAM Execution Role for Lambda

```bash
aws iam create-role \
  --role-name zendesk-sme-finder-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name zendesk-sme-finder-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name zendesk-sme-finder-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

### 2. Deploy Zendesk Action Group Lambda

```bash
cd lambdas/action-groups/zendesk

# Install dependencies
pip install -r requirements.txt -t package/

# Copy handler
cp handler.py package/

# Create deployment package
cd package
zip -r ../zendesk-action-group.zip .
cd ..

# Deploy Lambda
aws lambda create-function \
  --function-name zendesk-sme-finder-zendesk-actions \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/zendesk-sme-finder-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://zendesk-action-group.zip \
  --timeout 60 \
  --memory-size 512 \
  --environment Variables='{
    "ZENDESK_SECRET_NAME": "zendesk-sme-finder/zendesk-credentials"
  }'
```

Note the Lambda ARN - you'll need it for the Bedrock Agent.

### 3. Deploy Slack Action Group Lambda

```bash
cd lambdas/action-groups/slack

# Install dependencies
pip install -r requirements.txt -t package/

# Copy handler
cp handler.py package/

# Create deployment package
cd package
zip -r ../slack-action-group.zip .
cd ..

# Deploy Lambda
aws lambda create-function \
  --function-name zendesk-sme-finder-slack-actions \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/zendesk-sme-finder-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://slack-action-group.zip \
  --timeout 60 \
  --memory-size 512 \
  --environment Variables='{
    "SLACK_SECRET_NAME": "zendesk-sme-finder/slack-credentials"
  }'
```

Note the Lambda ARN - you'll need it for the Bedrock Agent.

## Bedrock Agent Configuration

### 1. Create IAM Role for Bedrock Agent

```bash
aws iam create-role \
  --role-name zendesk-sme-finder-bedrock-agent-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "bedrock.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Create and attach policy for Bedrock Agent
aws iam put-role-policy \
  --role-name zendesk-sme-finder-bedrock-agent-role \
  --policy-name BedrockAgentPermissions \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "bedrock:InvokeModel",
          "bedrock:Retrieve"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": "lambda:InvokeFunction",
        "Resource": [
          "arn:aws:lambda:REGION:ACCOUNT_ID:function:zendesk-sme-finder-zendesk-actions",
          "arn:aws:lambda:REGION:ACCOUNT_ID:function:zendesk-sme-finder-slack-actions"
        ]
      }
    ]
  }'
```

### 2. Create Bedrock Agent

Navigate to Bedrock Console > Agents > Create Agent

#### Basic Configuration

- Agent name: `zendesk-sme-finder-agent`
- Description: `AI agent for finding SMEs to help with Zendesk tickets`
- Model: Claude 3.5 Sonnet
- IAM role: `zendesk-sme-finder-bedrock-agent-role`

#### Agent Instructions

Copy the following instructions into the agent:

```
You are an intelligent FDE (Field Development Engineer) finder for Zendesk support tickets. Your goal is to analyze tickets and recommend the best FDEs to help resolve them.

WORKFLOW:
1. When given a ticket ID, fetch the ticket details from Zendesk
2. Analyze the ticket subject, description, and assigned engineer
3. Search the similar-tickets knowledge base to find historically similar tickets and successful resolutions
4. Search the fde-profiles knowledge base to find FDEs with relevant expertise
5. Rank FDEs based on:
   - Technical expertise match (highest priority)
   - Past success with similar issues
   - Customer satisfaction scores
   - Average resolution time
   - Current availability
6. Create a Slack conversation with the ticket's assigned engineer and top 3 recommended FDEs
7. Update the Zendesk ticket with recommendations and Slack conversation link

RESPONSE FORMAT:
Always return a JSON response with:
{
  "ticket_id": "the ticket ID",
  "ticket_subject": "brief subject",
  "assigned_engineer": "engineer name",
  "recommended_fdes": [
    {
      "name": "FDE name",
      "expertise_match": "explanation of why this FDE is a good match",
      "confidence_score": 0.0-1.0,
      "past_successes": "relevant past tickets or projects"
    }
  ],
  "similar_tickets": [
    {
      "ticket_id": "past ticket ID",
      "similarity": "what makes it similar",
      "resolution": "how it was resolved",
      "assigned_fde": "who resolved it"
    }
  ],
  "slack_conversation_url": "URL to the created Slack conversation",
  "zendesk_updated": true/false
}

GUIDELINES:
- Always recommend exactly 3 FDEs unless fewer are available
- Provide clear reasoning for each recommendation
- If confidence is low (< 0.6), mention this in the response
- Handle errors gracefully and return informative error messages
- Ensure the Slack conversation includes all necessary context
```

#### Action Groups Configuration

Add two Action Groups:

**Zendesk Operations Action Group**

- Name: `zendesk-operations`
- Description: `Fetch and update Zendesk tickets`
- Lambda function: Select `zendesk-sme-finder-zendesk-actions`
- API Schema:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Zendesk Operations API",
    "version": "1.0.0",
    "description": "API for fetching and updating Zendesk tickets"
  },
  "paths": {
    "/fetch_ticket": {
      "post": {
        "summary": "Fetch ticket details from Zendesk",
        "description": "Retrieves complete ticket information including subject, description, and assigned engineer",
        "operationId": "fetchTicket",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "ticket_id": {
                    "type": "string",
                    "description": "The Zendesk ticket ID"
                  }
                },
                "required": ["ticket_id"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Ticket details retrieved successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "ticket_id": {"type": "string"},
                    "subject": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string"},
                    "priority": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "assigned_engineer": {"type": "string"},
                    "engineer_email": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/update_ticket": {
      "post": {
        "summary": "Update Zendesk ticket with FDE recommendations",
        "description": "Adds an internal comment to the ticket with recommended FDEs and Slack conversation link",
        "operationId": "updateTicket",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "ticket_id": {"type": "string"},
                  "slack_conversation_url": {"type": "string"},
                  "recommended_fdes": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "name": {"type": "string"},
                        "expertise_match": {"type": "string"},
                        "confidence_score": {"type": "number"}
                      }
                    }
                  }
                },
                "required": ["ticket_id", "slack_conversation_url", "recommended_fdes"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Ticket updated successfully"
          }
        }
      }
    }
  }
}
```

**Slack Operations Action Group**

- Name: `slack-operations`
- Description: `Create Slack conversations with engineers and FDEs`
- Lambda function: Select `zendesk-sme-finder-slack-actions`
- API Schema:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Slack Operations API",
    "version": "1.0.0",
    "description": "API for creating Slack conversations"
  },
  "paths": {
    "/create_conversation": {
      "post": {
        "summary": "Create Slack conversation for ticket collaboration",
        "description": "Creates a Slack channel, invites engineer and FDEs, and posts ticket context",
        "operationId": "createConversation",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "ticket_id": {"type": "string"},
                  "engineer_slack_id": {"type": "string"},
                  "fde_slack_ids": {
                    "type": "array",
                    "items": {"type": "string"}
                  },
                  "ticket_subject": {"type": "string"},
                  "zendesk_url": {"type": "string"}
                },
                "required": ["ticket_id", "engineer_slack_id", "fde_slack_ids", "ticket_subject", "zendesk_url"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Conversation created successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "conversation_url": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Knowledge Bases Configuration

Add both Knowledge Bases:

1. Select `similar-tickets-kb` - "Use for finding historically similar tickets"
2. Select `fde-profiles-kb` - "Use for finding FDEs with relevant expertise"

### 3. Create Agent Alias

After creating the agent:

1. Click "Prepare" to validate the configuration
2. Click "Create Alias"
3. Name: `production`
4. Description: `Production alias for FDE Finder agent`
5. Note the Agent ID and Alias ID - you'll need them for the Orchestration Lambda

## Orchestration Lambda Deployment

### 1. Update Environment Variables

Edit `lambdas/orchestration/handler.py` and update:

```python
AGENT_ID = 'YOUR_AGENT_ID'  # From previous step
AGENT_ALIAS_ID = 'YOUR_ALIAS_ID'  # From previous step
```

### 2. Deploy Lambda

```bash
cd lambdas/orchestration

# Install dependencies
pip install -r requirements.txt -t package/

# Copy handler and shared utilities
cp handler.py package/
cp -r ../../shared package/

# Create deployment package
cd package
zip -r ../orchestration-lambda.zip .
cd ..

# Deploy Lambda
aws lambda create-function \
  --function-name zendesk-sme-finder-orchestration \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/zendesk-sme-finder-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://orchestration-lambda.zip \
  --timeout 120 \
  --memory-size 1024 \
  --environment Variables='{
    "AGENT_ID": "YOUR_AGENT_ID",
    "AGENT_ALIAS_ID": "YOUR_ALIAS_ID"
  }'
```

Note the Lambda ARN - you'll need it for API Gateway.

## API Gateway Setup

### 1. Create REST API

```bash
# Create API
aws apigateway create-rest-api \
  --name zendesk-sme-finder-api \
  --description "API for Zendesk SME Finder" \
  --endpoint-configuration types=REGIONAL
```

Note the API ID.

### 2. Create Resource and Method

```bash
# Get root resource ID
ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id YOUR_API_ID \
  --query 'items[0].id' \
  --output text)

# Create /find-fdes resource
aws apigateway create-resource \
  --rest-api-id YOUR_API_ID \
  --parent-id $ROOT_ID \
  --path-part find-fdes

# Note the resource ID
RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id YOUR_API_ID \
  --query 'items[?path==`/find-fdes`].id' \
  --output text)

# Create POST method
aws apigateway put-method \
  --rest-api-id YOUR_API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --authorization-type NONE \
  --api-key-required

# Create Lambda integration
aws apigateway put-integration \
  --rest-api-id YOUR_API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:REGION:ACCOUNT_ID:function:zendesk-sme-finder-orchestration/invocations

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name zendesk-sme-finder-orchestration \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:REGION:ACCOUNT_ID:YOUR_API_ID/*/*"
```

### 3. Create API Key and Usage Plan

```bash
# Create API key
aws apigateway create-api-key \
  --name zendesk-sme-finder-key \
  --enabled

# Note the API key ID and value

# Create usage plan
aws apigateway create-usage-plan \
  --name zendesk-sme-finder-plan \
  --throttle burstLimit=100,rateLimit=50 \
  --quota limit=10000,period=MONTH

# Note the usage plan ID

# Associate API key with usage plan
aws apigateway create-usage-plan-key \
  --usage-plan-id YOUR_USAGE_PLAN_ID \
  --key-id YOUR_API_KEY_ID \
  --key-type API_KEY
```

### 4. Deploy API

```bash
# Create deployment
aws apigateway create-deployment \
  --rest-api-id YOUR_API_ID \
  --stage-name production \
  --stage-description "Production stage"
```

Your API endpoint will be:
```
https://YOUR_API_ID.execute-api.REGION.amazonaws.com/production/find-fdes
```

## Streamlit Frontend Deployment

### Option 1: Local Development

```bash
cd frontend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
API_ENDPOINT=https://YOUR_API_ID.execute-api.REGION.amazonaws.com/production/find-fdes
API_KEY=YOUR_API_KEY
EOF

# Run Streamlit
streamlit run app.py
```

Access at http://localhost:8501

### Option 2: Deploy to EC2

```bash
# Launch EC2 instance (t3.small recommended)
# Connect via SSH

# Install dependencies
sudo yum update -y
sudo yum install python3.11 -y
sudo pip3 install streamlit requests

# Copy application files
scp -i your-key.pem -r frontend/ ec2-user@your-instance:/home/ec2-user/

# SSH to instance
ssh -i your-key.pem ec2-user@your-instance

# Create .env file
cd frontend
cat > .env << EOF
API_ENDPOINT=https://YOUR_API_ID.execute-api.REGION.amazonaws.com/production/find-fdes
API_KEY=YOUR_API_KEY
EOF

# Run as background service
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

Access at http://your-ec2-public-ip:8501

### Option 3: Deploy to ECS Fargate

Create `frontend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV API_ENDPOINT=""
ENV API_KEY=""

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Deploy using ECS:

```bash
# Build and push Docker image
docker build -t zendesk-sme-finder-frontend .
docker tag zendesk-sme-finder-frontend:latest YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/zendesk-sme-finder-frontend:latest
aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com
docker push YOUR_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/zendesk-sme-finder-frontend:latest

# Create ECS task definition and service (via console or CLI)
```

## Testing

### 1. Test Action Group Lambdas

```bash
# Test Zendesk Lambda
aws lambda invoke \
  --function-name zendesk-sme-finder-zendesk-actions \
  --payload '{"action": "fetch_ticket", "parameters": [{"name": "ticket_id", "value": "12345"}]}' \
  response.json

cat response.json

# Test Slack Lambda
aws lambda invoke \
  --function-name zendesk-sme-finder-slack-actions \
  --payload '{"action": "create_conversation", "parameters": [{"name": "ticket_id", "value": "12345"}, {"name": "engineer_slack_id", "value": "U01ABC123"}, {"name": "fde_slack_ids", "value": ["U02DEF456", "U03GHI789"]}, {"name": "ticket_subject", "value": "Test ticket"}, {"name": "zendesk_url", "value": "https://test.zendesk.com/agent/tickets/12345"}]}' \
  response.json

cat response.json
```

### 2. Test Bedrock Agent

Navigate to Bedrock Console > Agents > Your Agent > Test

Try: "Find FDEs for ticket 10001"

### 3. Test Orchestration Lambda

```bash
aws lambda invoke \
  --function-name zendesk-sme-finder-orchestration \
  --payload '{"body": "{\"ticket_id\": \"10001\"}"}' \
  response.json

cat response.json
```

### 4. Test API Gateway

```bash
curl -X POST https://YOUR_API_ID.execute-api.REGION.amazonaws.com/production/find-fdes \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"ticket_id": "10001"}'
```

### 5. Test Streamlit Frontend

1. Open Streamlit app in browser
2. Enter ticket ID: `10001`
3. Click "Find FDEs"
4. Verify recommendations appear
5. Check that Slack conversation was created
6. Verify Zendesk ticket was updated

## Monitoring and Troubleshooting

### CloudWatch Logs

All components write logs to CloudWatch:

- Zendesk Lambda: `/aws/lambda/zendesk-sme-finder-zendesk-actions`
- Slack Lambda: `/aws/lambda/zendesk-sme-finder-slack-actions`
- Orchestration Lambda: `/aws/lambda/zendesk-sme-finder-orchestration`
- Bedrock Agent: `/aws/bedrock/agents/YOUR_AGENT_ID`

### Common Issues

#### Issue: "Agent not found" error

Solution: Verify Agent ID and Alias ID in Orchestration Lambda environment variables

#### Issue: "Access denied" when invoking Lambda from Bedrock

Solution: Check IAM role for Bedrock Agent has `lambda:InvokeFunction` permission

#### Issue: "No results from Knowledge Base"

Solution: Ensure Knowledge Bases are synced. Navigate to Bedrock > Knowledge Bases > Your KB > Sync

#### Issue: "Zendesk API authentication failed"

Solution: Verify credentials in Secrets Manager are correct

#### Issue: "Slack conversation creation failed"

Solution: Check Slack bot has necessary permissions (channels:write, chat:write, users:read)

### Performance Optimization

1. **Lambda Cold Starts**: Enable provisioned concurrency for Orchestration Lambda if needed
2. **Knowledge Base Performance**: Use larger chunk sizes (500 tokens) for faster retrieval
3. **API Gateway Caching**: Enable caching for frequent queries
4. **Bedrock Agent Response Time**: Adjust max tokens and temperature for faster responses

## Cost Monitoring

Monitor costs in AWS Cost Explorer:

- Bedrock Agent invocations: ~$0.003 per invocation
- Knowledge Base queries: ~$0.0002 per query
- Lambda executions: Minimal (free tier likely covers)
- OpenSearch Serverless: ~$3.50/month per collection
- S3 storage: Minimal (< $1/month)

Expected monthly cost: $4-6 for moderate usage (100 tickets/month)

## Next Steps

1. Replace sample data with real historical tickets and FDE profiles
2. Set up automated sync of new tickets to Knowledge Base
3. Implement feedback loop to improve recommendations
4. Add authentication to Streamlit app
5. Set up CI/CD pipeline for deployments
6. Configure alerts for failures
7. Implement analytics dashboard for tracking FDE match success rates

## Support

For issues or questions:
- Check CloudWatch Logs for error details
- Review AWS Bedrock documentation
- Contact your AWS support team
