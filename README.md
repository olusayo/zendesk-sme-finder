# Zendesk FDE Finder

An intelligent AI system that analyzes Zendesk ticket content and matches engineers with the most relevant Field Development Experts (FDEs) using AWS Bedrock Agents, Knowledge Bases, and Action Groups.

## Problem Statement

Engineers waste time manually searching for expertise when stuck on complex tickets, leading to:
- Delayed customer resolutions
- Knowledge silos
- Inefficient resource allocation
- Decreased customer satisfaction

## Solution

An AI-powered system that:
1. **Analyzes ticket content** using Bedrock Agent with Claude 3.5 Sonnet
2. **Searches historical tickets** using Knowledge Bases for similar resolved issues
3. **Matches FDE expertise** from profiles and past successful resolutions
4. **Identifies top 3 FDEs** based on semantic similarity and past performance
5. **Facilitates collaboration** via automated Slack conversation creation

## Architecture Overview

![Streamlit-Bedrock-Zendesk Workflow](docs/architecture-diagram.pdf)

For detailed architecture information, see [ARCHITECTURE_V2.md](docs/ARCHITECTURE_V2.md)

### Simplified Flow

```
User (Streamlit App)
    |
    | 1. Enter Ticket ID OR Description
    |
Lambda Function URL (Direct Invoke)
    |
    | 2. POST with ticket_id and/or ticket_description
    |
Orchestration Lambda (Hybrid Workflow)
    |
    | 3. Invoke Bedrock Agent with mode-specific prompt
    |
Bedrock Agent (Claude 3.5 Sonnet)
    |
    ├── 4a. Action Group: Fetch Ticket from Zendesk (if ticket_id provided)
    ├── 4b. Knowledge Base: Find Similar Tickets
    ├── 4c. Knowledge Base: Find Matching FDEs
    ├── 4d. Action Group: Create Slack Conversation (if ticket_id provided)
    └── 4e. Action Group: Update Zendesk Ticket (if ticket_id provided)
    |
    | 5. Return recommendations with reasoning
    |
User (View Results in Streamlit)
```

## Key Components

### 1. **Streamlit Frontend**
- **Function**: User interface for entering ticket IDs or descriptions and viewing recommendations
- **Features**:
  - Hybrid input: Ticket ID OR description
  - Real-time FDE recommendations display with expertise reasoning
  - Similar tickets reference
  - Slack conversation link (when using ticket ID mode)

### 2. **Orchestration Lambda**
- **Function**: Invokes Bedrock Agent with hybrid workflow support and parses responses
- **Input**: Ticket ID and/or ticket description from Lambda Function URL
- **Output**: Top 3 FDE recommendations with expertise reasoning and similar tickets
- **Workflow Modes**:
  - Mode 1: Ticket ID only (try full Zendesk/Slack workflow)
  - Mode 2: Ticket ID + description (with fallback to description)
  - Mode 3: Description only (skip external APIs, use Knowledge Bases)

### 3. **Bedrock Agent (Claude 3.5 Sonnet)**
- **Function**: AI orchestration and reasoning
- **Capabilities**:
  - Analyzes ticket content
  - Queries Knowledge Bases for similar tickets and FDE expertise
  - Invokes Action Groups for Zendesk and Slack operations
  - Ranks FDEs based on expertise match and past success
- **Output**: Top 3 FDE recommendations with justification

### 4. **Action Groups (Lambda Functions)**
- **Zendesk Operations**:
  - Fetch ticket details and assigned engineer
  - Update ticket with FDE recommendations
- **Slack Operations**:
  - Create Slack conversation with engineer and FDEs
  - Post ticket context and recommendations

### 5. **Knowledge Bases (OpenSearch Serverless)**
- **Similar Tickets KB**: Historical tickets with resolutions
  - Data source: `s3://genai-enablement-team3-us-east-1/tickets/`
  - Contains: CSV files with ticket IDs, subjects, descriptions, and resolutions
- **FDE Profiles KB**: FDE expertise, certifications, and past successes
  - Data source: `s3://genai-enablement-team3-us-east-1/certificates/`
  - Contains: FDE names, emails, certifications, expertise areas
- **Embeddings**: Amazon Titan Embeddings v2

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| AI Orchestration | AWS Bedrock Agents | Built-in reasoning and workflow management |
| LLM | Claude 3.5 Sonnet | Superior reasoning and analysis |
| Embeddings | Amazon Titan Embeddings v2 | Native Bedrock integration |
| Vector Database | OpenSearch Serverless | Managed by Bedrock Knowledge Bases |
| Action Groups | Lambda (Python 3.11) | Cost-effective integrations |
| API | Lambda Function URLs | Direct invocation with 15-minute timeout |
| Frontend | Streamlit (ECS Fargate) | Simple, fast Python web framework |
| Storage | S3 | Knowledge Base data source |
| Monitoring | CloudWatch | Native observability |

## Project Structure

```
Zendesk_SME_Finder/
├── frontend/                      # Streamlit web application
│   ├── app.py                    # Main Streamlit app
│   └── requirements.txt          # Python dependencies
├── lambdas/
│   ├── orchestration/            # Orchestration Lambda
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── action-groups/            # Action Group Lambdas
│       ├── zendesk/              # Zendesk operations
│       │   ├── handler.py
│       │   └── requirements.txt
│       └── slack/                # Slack operations
│           ├── handler.py
│           └── requirements.txt
├── data/
│   └── knowledge-bases/          # Sample data for KBs
│       ├── similar-tickets/      # Historical tickets
│       └── fde-profiles/         # FDE expertise profiles
├── shared/                       # Shared Python utilities
│   ├── logging_utils.py
│   ├── metrics_utils.py
│   └── aws_clients.py
└── docs/                         # Documentation
    ├── ARCHITECTURE_V2.md        # Architecture design
    ├── DEPLOYMENT_GUIDE.md       # Deployment instructions
    └── architecture-diagram.pdf  # Visual diagram
```

## Quick Start

### Prerequisites

- AWS Account with Bedrock access (Claude 3.5 Sonnet, Amazon Titan Embeddings v2)
- AWS CLI configured
- Python 3.11+
- Zendesk API credentials (optional - required only for full Zendesk/Slack workflow)
- Slack Bot token (optional - required only for full Zendesk/Slack workflow)

### Deployment

Choose your deployment method:

**Option 1: Terraform (Recommended) - 15 minutes**
- Automated infrastructure deployment
- Repeatable and version-controlled
- See [terraform/TERRAFORM_DEPLOYMENT_GUIDE.md](terraform/TERRAFORM_DEPLOYMENT_GUIDE.md)

**Option 2: Manual Deployment**
- Step-by-step comprehensive guide
- Perfect for AWS beginners
- See [COMPLETE_DEPLOYMENT_GUIDE.md](COMPLETE_DEPLOYMENT_GUIDE.md)

**High-level steps** (both methods):

1. Enable Bedrock model access
2. Create Knowledge Bases with sample data
3. Deploy Lambda functions (automated with Terraform)
4. Create and configure Bedrock Agent
5. Set up API Gateway (automated with Terraform)
6. Deploy Streamlit frontend

### Local Testing

```bash
# 1. Clone repository
git clone https://github.com/olusayo/git-repository.git
cd git-repository/Zendesk_SME_Finder

# 2. Run Streamlit locally
cd frontend
pip install -r requirements.txt

# 3. Configure environment
cat > .env << EOF
API_ENDPOINT=https://your-lambda-url.lambda-url.region.on.aws/
API_KEY=
EOF

# 4. Run app
streamlit run app.py
```

## Configuration

### Secrets Manager

Store credentials in AWS Secrets Manager:

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

### Lambda Environment Variables

**Orchestration Lambda**:
- `BEDROCK_AGENT_ID`: Bedrock Agent ID
- `BEDROCK_AGENT_ALIAS_ID`: Bedrock Agent Alias ID

**Action Group Lambdas**:
- `ZENDESK_SECRET_NAME`: zendesk-sme-finder/zendesk-credentials
- `SLACK_SECRET_NAME`: zendesk-sme-finder/slack-credentials

### Streamlit Frontend

Create `.env` file or set ECS environment variables:
```bash
API_ENDPOINT=https://your-lambda-url.lambda-url.region.on.aws/
API_KEY=
```

## Learning Outcomes

Through this project, you'll learn:
- **Bedrock Agents**: AI orchestration with Action Groups and Knowledge Bases
- **RAG Systems**: Building retrieval-augmented generation with Bedrock
- **Vector Search**: Semantic search with OpenSearch Serverless
- **AWS Bedrock**: Claude 3.5 Sonnet and Titan Embeddings integration
- **API Integrations**: Zendesk and Slack SDKs
- **Serverless Architecture**: Lambda, API Gateway, managed services
- **Streamlit**: Building interactive web UIs with Python
- **Cost Optimization**: Simplified architecture, 85% cost reduction

## Performance Metrics

### Target KPIs
- **Match Accuracy**: >85% engineer satisfaction with FDE recommendations
- **Response Time**: <10 seconds from ticket ID entry to results
- **Resolution Improvement**: 30% reduction in time-to-expert
- **Cost Efficiency**: <$0.05 per ticket processed

### Current Status
- **Phase**: Core Implementation Complete
- **Completion**: 50% (Ready for deployment and testing)

## Monitoring & Observability

### CloudWatch Logs
- **Orchestration Lambda**: `/aws/lambda/zendesk-sme-finder-orchestration`
- **Zendesk Action Group**: `/aws/lambda/zendesk-sme-finder-zendesk-actions`
- **Slack Action Group**: `/aws/lambda/zendesk-sme-finder-slack-actions`
- **Bedrock Agent**: `/aws/bedrock/agents/{AGENT_ID}`

### Metrics to Monitor
- **Bedrock Agent Invocations**: Request count and latency
- **Knowledge Base Queries**: Retrieval accuracy and performance
- **Lambda Errors**: Action Group failures
- **Lambda Function URL**: Request rate and 4xx/5xx errors

### Alerts
- **High Error Rate**: >5% Lambda failures
- **High Latency**: >30s Bedrock Agent response time
- **Cost Anomaly**: Daily Bedrock spend >$10

## Security

- **IAM**: Least-privilege roles for all services
- **Secrets**: Stored in AWS Secrets Manager
- **Encryption**: At-rest (S3, Pinecone) and in-transit (TLS)
- **API Keys**: Rotated quarterly
- **Audit Logging**: CloudTrail for all API calls

## Cost Estimation

**Monthly costs** (estimated for 100 tickets/month):

| Service | Usage | Cost |
|---------|-------|------|
| Bedrock Claude 3.5 Sonnet | 200K tokens | ~$0.60 |
| Bedrock Titan Embeddings v2 | 50K tokens | ~$0.10 |
| OpenSearch Serverless | 2 collections | ~$1.50 |
| Lambda | 300 invocations | ~$0.05 |
| Lambda Function URL | 100 requests | ~$0.00 |
| ECS Fargate | 1 task (0.25 vCPU) | ~$3.00 |
| S3 | 1GB storage | ~$0.02 |
| CloudWatch | Logs/metrics | ~$1.00 |
| **Total** | | **~$6.27/month** |

**Notes**:
- Lambda Function URLs have no additional charge (only Lambda invocation costs)
- Costs may be higher during initial testing and development
- Production costs depend on actual usage volume

## Next Steps

After deployment:

1. **Replace Sample Data**: Update Knowledge Bases with real historical tickets and FDE profiles
2. **Test with Real Tickets**: Validate recommendations with actual Zendesk tickets
3. **Collect Feedback**: Track FDE match accuracy and engineer satisfaction
4. **Optimize Prompts**: Refine Bedrock Agent instructions based on results
5. **Set Up Monitoring**: Configure CloudWatch alarms and dashboards
6. **Implement Authentication**: Add user auth to Streamlit frontend
7. **Automate Sync**: Schedule regular updates to Knowledge Bases

## Documentation

- **[Complete Deployment Guide](COMPLETE_DEPLOYMENT_GUIDE.md)**: Comprehensive step-by-step deployment guide
- **[Hybrid Workflow Guide](HYBRID_WORKFLOW_GUIDE.md)**: Using the system with or without Zendesk/Slack API keys
- **[Bedrock Agent Instructions](BEDROCK_AGENT_INSTRUCTIONS.md)**: Agent configuration and prompts
- **[Architecture V2](docs/ARCHITECTURE_V2.md)**: Complete architecture design
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)**: Additional deployment reference
- **[Architecture Diagram](docs/architecture-diagram.pdf)**: Visual workflow diagram
- **[Terraform Deployment Guide](terraform/TERRAFORM_DEPLOYMENT_GUIDE.md)**: Infrastructure as Code deployment

## Support

For questions or issues, see the deployment guide troubleshooting section.

---

**Built using AWS Bedrock Agents, Claude 3.5 Sonnet, and Streamlit**
