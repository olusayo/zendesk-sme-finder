# Architecture V2 - Zendesk FDE Finder (Bedrock Agent Approach)

## Overview

The Zendesk FDE (Field Development Engineer) Finder is a streamlined AI system that uses AWS Bedrock Agents to intelligently match engineers with Field Development Experts for complex support tickets.

**Key Simplification**: Uses Bedrock Agents with Action Groups and Knowledge Bases instead of complex orchestration with Step Functions, ECS, and Pinecone.

## Architecture Principles

### 1. Simplicity First
- **Single Bedrock Agent**: Handles all orchestration logic
- **Action Groups**: Simple Lambda functions for integrations
- **Knowledge Bases**: Managed vector search (no Pinecone needed)
- **Synchronous Flow**: User gets results immediately

### 2. AWS-Native Services
- **Bedrock Agent**: AI orchestration and reasoning
- **Bedrock Knowledge Bases**: Vector search for similar tickets and FDEs
- **Lambda**: Lightweight integrations (Zendesk, Slack)
- **API Gateway**: REST API endpoint
- **Streamlit**: Simple, user-friendly frontend

## System Architecture

### Architecture Diagram

![Streamlit-Bedrock-Zendesk Workflow](architecture-diagram.pdf)

The diagram above shows the complete workflow from user interaction through to external service integration.

### High-Level Flow

```
User (Streamlit App)
    |
    | 1. Enter Ticket ID
    |
API Gateway (REST API)
    |
    | 2. POST /find-fde
    |
Orchestration Lambda
    |
    | 3. Invoke Bedrock Agent
    |
Bedrock Agent
    |
    ├── 4a. Action Group 1: Fetch Ticket (Zendesk API)
    |   └── Returns: ticket details + assigned engineer
    |
    ├── 4b. Knowledge Base 1: Find Similar Tickets
    |   └── Returns: 3 similar resolved tickets
    |
    ├── 4c. Knowledge Base 2: Find Recommended FDEs
    |   └── Returns: 3 FDEs with expertise match
    |
    ├── 4d. Action Group 2: Create Slack Conversation
    |   └── Creates: Slack channel with engineer + 3 FDEs
    |
    └── 4e. Action Group 1: Update Zendesk Ticket
        └── Updates: Ticket with Slack link + FDE recommendations
    |
    | 5. Return results
    |
Orchestration Lambda
    |
    | 6. Format response
    |
API Gateway
    |
    | 7. JSON response
    |
Streamlit App
    |
    | 8. Display results to user
    |
User sees:
- Recommended FDEs
- Similar tickets
- Slack conversation link
```

## Component Details

### 1. Streamlit Frontend

**Purpose**: Simple web interface for engineers to request FDE matches

**Features**:
- Text input for ticket ID
- Submit button
- Display results:
  - Recommended FDEs (names, expertise, confidence scores)
  - Similar resolved tickets
  - Slack conversation link
  - Zendesk ticket link

**Technology**:
- Streamlit (Python)
- Requests library for API calls
- Simple styling with Streamlit components

**File**: `frontend/app.py`

### 2. API Gateway

**Purpose**: REST API endpoint for the Streamlit app

**Configuration**:
- **Endpoint**: `/find-fde`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "ticket_id": "12345"
  }
  ```
- **Response**:
  ```json
  {
    "ticket_id": "12345",
    "recommended_fdes": [
      {
        "name": "John Doe",
        "email": "john@example.com",
        "expertise": ["PostgreSQL", "AWS RDS"],
        "confidence": 0.92,
        "slack_id": "U12345"
      }
    ],
    "similar_tickets": [
      {
        "ticket_id": "11111",
        "subject": "PostgreSQL performance issue",
        "resolution": "Optimized query indexing"
      }
    ],
    "slack_conversation_url": "https://slack.com/archives/C12345",
    "zendesk_url": "https://example.zendesk.com/tickets/12345"
  }
  ```

**Integration**: Lambda proxy integration with Orchestration Lambda

### 3. Orchestration Lambda

**Purpose**: Invoke Bedrock Agent and format responses

**Responsibilities**:
- Validate incoming request (ticket_id)
- Invoke Bedrock Agent with ticket_id
- Parse Bedrock Agent response
- Format JSON response for API Gateway
- Error handling and logging

**Technology**:
- Runtime: Python 3.12
- Memory: 512 MB
- Timeout: 120 seconds (to allow for Bedrock Agent execution)

**File**: `lambdas/orchestration/handler.py`

**Code Structure**:
```python
def lambda_handler(event, context):
    # 1. Extract ticket_id from request
    ticket_id = json.loads(event['body'])['ticket_id']

    # 2. Invoke Bedrock Agent
    bedrock_agent = boto3.client('bedrock-agent-runtime')
    response = bedrock_agent.invoke_agent(
        agentId='AGENT_ID',
        agentAliasId='ALIAS_ID',
        sessionId=f"session-{ticket_id}",
        inputText=f"Find FDEs for ticket {ticket_id}"
    )

    # 3. Parse streaming response
    result = parse_agent_response(response)

    # 4. Return formatted response
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

### 4. Bedrock Agent

**Purpose**: Orchestrate the entire FDE matching process using AI reasoning

**Agent Configuration**:
- **Model**: Claude Sonnet 4.5
- **Instructions**:
  ```
  You are an expert at matching support tickets with Field Development Engineers (FDEs).

  Your task is to:
  1. Fetch the ticket details from Zendesk using the ticket ID
  2. Find 3 similar resolved tickets from the knowledge base
  3. Find 3 recommended FDEs based on the ticket content and similar tickets
  4. Create a Slack conversation with the assigned engineer and 3 FDEs
  5. Update the Zendesk ticket with Slack link and FDE recommendations

  Always execute these steps in order and return structured results.
  ```

**Action Groups**:

#### Action Group 1: Zendesk Operations
- **Name**: zendesk-operations
- **Description**: Fetch and update Zendesk tickets
- **Lambda Function**: `zendesk-action-group`
- **API Schema**:
  ```json
  {
    "openapi": "3.0.0",
    "paths": {
      "/fetch-ticket": {
        "post": {
          "description": "Fetch ticket details from Zendesk",
          "parameters": {
            "ticket_id": {
              "type": "string",
              "required": true
            }
          },
          "responses": {
            "200": {
              "description": "Ticket details including assigned engineer",
              "content": {
                "application/json": {
                  "schema": {
                    "type": "object",
                    "properties": {
                      "ticket_id": "string",
                      "subject": "string",
                      "description": "string",
                      "priority": "string",
                      "assigned_engineer": "object",
                      "tags": "array",
                      "created_at": "string"
                    }
                  }
                }
              }
            }
          }
        }
      },
      "/update-ticket": {
        "post": {
          "description": "Update Zendesk ticket with FDE info",
          "parameters": {
            "ticket_id": "string",
            "slack_url": "string",
            "recommended_fdes": "array"
          }
        }
      }
    }
  }
  ```

#### Action Group 2: Slack Operations
- **Name**: slack-operations
- **Description**: Create Slack conversations
- **Lambda Function**: `slack-action-group`
- **API Schema**:
  ```json
  {
    "openapi": "3.0.0",
    "paths": {
      "/create-conversation": {
        "post": {
          "description": "Create Slack conversation with engineer and FDEs",
          "parameters": {
            "ticket_id": "string",
            "engineer_slack_id": "string",
            "fde_slack_ids": "array",
            "message": "string"
          },
          "responses": {
            "200": {
              "description": "Slack conversation created",
              "content": {
                "application/json": {
                  "schema": {
                    "type": "object",
                    "properties": {
                      "conversation_url": "string",
                      "channel_id": "string"
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

**Knowledge Bases**:

#### Knowledge Base 1: Similar Tickets
- **Name**: similar-tickets-kb
- **Data Source**: `s3://genai-enablement-team3/tickets/` (ARN: `arn:aws:s3:::genai-enablement-team3/tickets/`)
- **Embeddings Model**: Amazon Titan Embeddings v2
- **Vector Store**: OpenSearch Serverless (managed by Bedrock)
- **Data Format**: JSON/CSV documents with historical ticket data
  ```json
  {
    "ticket_id": "11111",
    "subject": "PostgreSQL performance degradation",
    "description": "Database queries running slow...",
    "resolution": "Optimized query indexing and added connection pooling",
    "assigned_fde": "John Doe",
    "resolution_time_hours": 4,
    "technologies": ["PostgreSQL", "AWS RDS"],
    "success": true
  }
  ```

#### Knowledge Base 2: FDE Profiles
- **Name**: fde-profiles-kb
- **Data Source**: `s3://genai-enablement-team3/certificates/` (ARN: `arn:aws:s3:::genai-enablement-team3/certificates/`)
- **Embeddings Model**: Amazon Titan Embeddings v2
- **Vector Store**: OpenSearch Serverless (managed by Bedrock)
- **Data Format**: CSV/JSON documents with FDE expertise and certification data
  ```json
  {
    "fde_id": "fde001",
    "name": "John Doe",
    "email": "john@example.com",
    "slack_id": "U12345",
    "expertise": [
      "PostgreSQL database optimization",
      "AWS RDS performance tuning",
      "Query optimization and indexing"
    ],
    "certifications": ["AWS Solutions Architect", "PostgreSQL Certified"],
    "years_experience": 8,
    "successful_tickets": 45,
    "specialization": "Database Performance"
  }
  ```

### 5. Action Group Lambda Functions

#### Zendesk Action Group Lambda

**File**: `lambdas/action-groups/zendesk/handler.py`

**Responsibilities**:
- Handle `/fetch-ticket` API call
- Handle `/update-ticket` API call
- Integrate with Zendesk API

**Code Structure**:
```python
def lambda_handler(event, context):
    # Parse action and parameters
    action = event['actionGroup']
    api_path = event['apiPath']
    parameters = event['parameters']

    if api_path == '/fetch-ticket':
        return fetch_ticket(parameters['ticket_id'])
    elif api_path == '/update-ticket':
        return update_ticket(
            parameters['ticket_id'],
            parameters['slack_url'],
            parameters['recommended_fdes']
        )

def fetch_ticket(ticket_id):
    # Call Zendesk API
    zendesk = ZendeskClient()
    ticket = zendesk.get_ticket(ticket_id)

    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'zendesk-operations',
            'apiPath': '/fetch-ticket',
            'httpMethod': 'POST',
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(ticket)
                }
            }
        }
    }
```

#### Slack Action Group Lambda

**File**: `lambdas/action-groups/slack/handler.py`

**Responsibilities**:
- Create Slack conversation
- Add engineer and FDEs to conversation
- Post initial message with ticket link

**Code Structure**:
```python
def lambda_handler(event, context):
    # Parse parameters
    parameters = event['parameters']

    # Create Slack conversation
    slack = SlackClient()
    conversation = slack.create_conversation(
        ticket_id=parameters['ticket_id'],
        engineer_id=parameters['engineer_slack_id'],
        fde_ids=parameters['fde_slack_ids'],
        message=parameters['message']
    )

    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'slack-operations',
            'apiPath': '/create-conversation',
            'httpMethod': 'POST',
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({
                        'conversation_url': conversation['url'],
                        'channel_id': conversation['channel_id']
                    })
                }
            }
        }
    }
```

## Data Flow Example

### Request Flow

1. **User Input** (Streamlit):
   ```
   Ticket ID: 12345
   [Submit]
   ```

2. **API Request**:
   ```http
   POST https://api.example.com/find-fde
   Content-Type: application/json

   {"ticket_id": "12345"}
   ```

3. **Orchestration Lambda** invokes Bedrock Agent:
   ```python
   response = bedrock_agent.invoke_agent(
       agentId='AGENT_ID',
       agentAliasId='ALIAS_ID',
       sessionId='session-12345',
       inputText='Find FDEs for ticket 12345'
   )
   ```

4. **Bedrock Agent executes**:
   - Step 1: Calls Action Group 1 → `/fetch-ticket` → Gets ticket details
   - Step 2: Queries Knowledge Base 1 → Gets 3 similar tickets
   - Step 3: Queries Knowledge Base 2 → Gets 3 recommended FDEs
   - Step 4: Calls Action Group 2 → `/create-conversation` → Creates Slack channel
   - Step 5: Calls Action Group 1 → `/update-ticket` → Updates Zendesk

5. **Response returned** to Streamlit:
   ```json
   {
     "recommended_fdes": [...],
     "similar_tickets": [...],
     "slack_conversation_url": "...",
     "zendesk_url": "..."
   }
   ```

## Infrastructure Components

### Required AWS Resources

1. **Bedrock Agent**
   - Agent ID
   - Agent Alias
   - Instruction prompt
   - 2 Action Groups
   - 2 Knowledge Bases

2. **Lambda Functions** (3 total)
   - Orchestration Lambda
   - Zendesk Action Group Lambda
   - Slack Action Group Lambda

3. **API Gateway**
   - REST API
   - POST /find-fde endpoint
   - Lambda proxy integration

4. **S3 Buckets** (2 total)
   - Historical tickets data
   - FDE profiles data

5. **OpenSearch Serverless** (managed by Bedrock)
   - 2 collections (one per Knowledge Base)

6. **IAM Roles**
   - Bedrock Agent execution role
   - Lambda execution roles
   - API Gateway role

### Cost Estimation (Monthly)

Based on 500 requests/month:

| Service | Usage | Cost |
|---------|-------|------|
| Bedrock Agent (Claude Sonnet 4.5) | 500 sessions × 2K tokens | ~$1.50 |
| Bedrock Knowledge Bases | 1000 queries | ~$0.50 |
| Lambda | 1500 invocations | ~$0.10 |
| API Gateway | 500 requests | ~$0.002 |
| OpenSearch Serverless | 2 collections | ~$1.50 |
| S3 | 10GB storage | ~$0.23 |
| **Total** | | **~$3.85/month** |

**10x cheaper** than the previous architecture!

## Advantages Over Previous Architecture

### Simplicity
- ❌ No Pinecone (Knowledge Bases replace it)
- ❌ No Step Functions (Bedrock Agent handles orchestration)
- ❌ No ECS Fargate (not needed)
- ❌ No complex embedding pipeline
- ✅ Single Bedrock Agent coordinates everything

### Cost
- Previous: ~$27/month
- New: ~$4/month
- Savings: ~85% reduction

### Maintenance
- Fewer components to monitor
- AWS-native services (better integration)
- Simpler debugging (Bedrock Agent traces)

### User Experience
- Synchronous responses (immediate feedback)
- Simple UI (Streamlit)
- Easy to test (just enter ticket ID)

## Security

### Authentication & Authorization
- API Gateway: API Key authentication
- Bedrock Agent: IAM role-based access
- Action Groups: Assume agent execution role

### Data Protection
- S3: Encryption at rest (AES-256)
- OpenSearch Serverless: Encryption enabled
- Secrets Manager: Zendesk & Slack credentials
- TLS: All API communications

### Network Security
- API Gateway: CORS configured
- Lambda: VPC optional (for Zendesk/Slack access)
- Knowledge Bases: Private access only

## Monitoring

### CloudWatch Metrics
- API Gateway: Request count, latency, errors
- Lambda: Invocations, duration, errors
- Bedrock Agent: Invocations, token usage

### CloudWatch Logs
- Orchestration Lambda logs
- Action Group Lambda logs
- Bedrock Agent traces (execution steps)

### Alerts
- API Gateway 5xx errors > 5%
- Lambda errors > 2%
- Bedrock Agent failures

## Deployment

See `docs/DEPLOYMENT.md` for step-by-step deployment instructions.

## References

- [AWS Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [Bedrock Action Groups](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-groups.html)
- [Streamlit Documentation](https://docs.streamlit.io/)
