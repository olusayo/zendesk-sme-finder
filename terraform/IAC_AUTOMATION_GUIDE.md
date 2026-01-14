# Infrastructure as Code (IaC) Automation Guide

## Overview

This Terraform configuration now provides **fully automated deployment** of the entire Zendesk SME Finder infrastructure, including:

**Bedrock Agent** - AI orchestration with Claude Sonnet 4.5
**Knowledge Bases** - Vector search with OpenSearch Serverless
**Lambda Functions** - Orchestration and action groups
**Lambda Function URLs** - Direct invocation with 15-minute timeout
**S3 Data Buckets** - Knowledge Base data storage
**ECS Fargate Frontend** - Streamlit web application
**IAM Roles & Policies** - Least-privilege access
**Secrets Management** - Secure credential storage
**Networking** - VPC, ALB, and security groups

## What's New?

### Previously Manual Steps (Now Automated)

| Component | Before | After |
|-----------|--------|-------|
| **Bedrock Agent** | Manual console creation | `aws_bedrockagent_agent` (Terraform) |
| **Knowledge Bases** | Manual console creation | `aws_bedrockagent_knowledge_base` (Terraform) |
| **OpenSearch Collections** | Manual console creation | `aws_opensearchserverless_collection` (Terraform) |
| **S3 Data Buckets** | Manual bucket creation | `aws_s3_bucket` (Terraform) |
| **Lambda Function URL** | Manual configuration | `aws_lambda_function_url` (Terraform) |
| **Agent Action Groups** | Manual API schema setup | `aws_bedrockagent_agent_action_group` (Terraform) |
| **KB Associations** | Manual linking in console | `aws_bedrockagent_agent_knowledge_base_association` (Terraform) |

### New Terraform Modules

```
terraform/
├── s3_data.tf                 # NEW: S3 buckets for Knowledge Base data
├── opensearch.tf              # NEW: OpenSearch Serverless collections
├── knowledge_bases.tf         # NEW: Bedrock Knowledge Bases
├── bedrock_agent.tf           # NEW: Bedrock Agent with action groups
├── lambda_url.tf              # NEW: Lambda Function URL configuration
├── variables.tf               # UPDATED: New configuration options
├── outputs.tf                 # UPDATED: Comprehensive outputs
└── IAC_AUTOMATION_GUIDE.md    # THIS FILE
```

## One-Command Deployment

### Before (Manual - 2-3 hours)
```bash
# 1. Create S3 buckets manually in console
# 2. Upload data to S3
# 3. Create OpenSearch collections in console
# 4. Configure security policies manually
# 5. Create Knowledge Bases in console
# 6. Link data sources manually
# 7. Wait for KB sync
# 8. Create Bedrock Agent in console
# 9. Add action groups manually
# 10. Link Knowledge Bases manually
# 11. Create agent aliases manually
# 12. Deploy Lambda functions
# 13. Configure Lambda Function URL
# 14. Deploy ECS frontend
# Total: 2-3 hours of console clicking
```

### After (Automated - 15 minutes)
```bash
# 1. Configure variables
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars  # Add your credentials

# 2. Deploy everything
terraform init
terraform apply -auto-approve

# 3. Upload data to auto-created S3 bucket
aws s3 sync ./data/tickets/ s3://$(terraform output -raw s3_data_bucket)/tickets/
aws s3 sync ./data/fde-profiles/ s3://$(terraform output -raw s3_data_bucket)/fde-profiles/

# 4. Trigger Knowledge Base ingestion
# (Commands provided in terraform output)

# Done!
```

## Configuration Variables

### New Variables in `variables.tf`

```hcl
# Bedrock Agent Configuration
variable "bedrock_model_id" {
  description = "Bedrock foundation model ID for the agent"
  default     = "anthropic.claude-sonnet-4-5-20250929-v1:0"
}

variable "bedrock_embedding_model_id" {
  description = "Bedrock embedding model ID for Knowledge Bases"
  default     = "amazon.titan-embed-text-v2:0"
}

variable "enable_bedrock_agent" {
  description = "Whether to create Bedrock Agent via Terraform (true) or manually (false)"
  default     = true  # Set to false for manual agent creation
}

variable "enable_knowledge_bases" {
  description = "Whether to create Knowledge Bases via Terraform (true) or manually (false)"
  default     = true  # Set to false for manual KB creation
}

# Knowledge Base Configuration
variable "kb_chunking_strategy" {
  description = "Chunking strategy for Knowledge Bases"
  default     = "FIXED_SIZE"  # Options: FIXED_SIZE, HIERARCHICAL, SEMANTIC, NONE
}

variable "kb_chunk_max_tokens" {
  description = "Maximum tokens per chunk"
  default     = 300
}

variable "kb_chunk_overlap_percentage" {
  description = "Overlap percentage between chunks"
  default     = 20
}
```

### Minimal `terraform.tfvars` Example

```hcl
# Required Configuration
zendesk_domain    = "yourcompany.zendesk.com"
zendesk_email     = "your-email@example.com"
zendesk_api_token = "your-zendesk-api-token"

slack_bot_token = "xoxb-your-slack-bot-token"
slack_team_url  = "https://yourteam.slack.com"

# Optional Overrides (defaults work great)
# aws_region = "us-east-1"
# bedrock_model_id = "anthropic.claude-sonnet-4-5-20250929-v1:0"
# enable_bedrock_agent = true
# enable_knowledge_bases = true
```

## Deployment Steps

### Step 1: Prerequisites

```bash
# Install Terraform
brew install terraform  # macOS
# or
sudo apt-get install terraform  # Linux

# Configure AWS credentials
aws configure
# Verify: aws sts get-caller-identity

# Enable Bedrock models in AWS Console
# Go to Bedrock Console → Model access
# Enable: Claude Sonnet 4.5, Amazon Titan Embeddings v2
```

### Step 2: Configure Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars  # Edit with your actual values
```

### Step 3: Initialize Terraform

```bash
terraform init
```

Expected output:
```
Initializing modules...
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.x.x...

Terraform has been successfully initialized!
```

### Step 4: Review Plan

```bash
terraform plan
```

Review the resources that will be created:
- 1 Bedrock Agent
- 2 Agent Aliases (production, test)
- 2 Action Groups (Zendesk, Slack)
- 2 Knowledge Bases (tickets, FDE profiles)
- 2 OpenSearch Serverless collections
- 2 Knowledge Base data sources
- 1 S3 bucket for data
- 3 Lambda functions
- 1 Lambda Function URL
- 1 ECS cluster with Fargate service
- 1 Application Load Balancer
- Multiple IAM roles and policies
- Secrets Manager secrets
- CloudWatch Log Groups

**Total: ~40-50 resources**

### Step 5: Deploy Infrastructure

```bash
terraform apply -auto-approve
```

This will take 10-15 minutes.

### Step 6: Upload Knowledge Base Data

```bash
# Get the S3 bucket name
BUCKET=$(terraform output -raw s3_data_bucket_name)

# Upload your ticket data
aws s3 sync ./data/tickets/ s3://$BUCKET/tickets/

# Upload your FDE profile data
aws s3 sync ./data/fde-profiles/ s3://$BUCKET/fde-profiles/
```

### Step 7: Trigger Knowledge Base Ingestion

```bash
# Get Knowledge Base and Data Source IDs
TICKETS_KB_ID=$(terraform output -json bedrock_resources | jq -r '.tickets_kb_id')
TICKETS_DS_ID=$(terraform output -json bedrock_resources | jq -r '.tickets_data_source')
FDE_KB_ID=$(terraform output -json bedrock_resources | jq -r '.fde_profiles_kb_id')
FDE_DS_ID=$(terraform output -json bedrock_resources | jq -r '.fde_profiles_data_source')

# Start ingestion jobs
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $TICKETS_KB_ID \
  --data-source-id $TICKETS_DS_ID

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $FDE_KB_ID \
  --data-source-id $FDE_DS_ID

# Monitor ingestion status
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $TICKETS_KB_ID \
  --data-source-id $TICKETS_DS_ID
```

### Step 8: Access Your Application

```bash
# Get the frontend URL
terraform output frontend_url

# Get the Lambda Function URL (for direct API access)
terraform output lambda_function_url

# Test the API
LAMBDA_URL=$(terraform output -raw lambda_function_url)
curl -X POST "$LAMBDA_URL" \
  -H "Content-Type: application/json" \
  -d '{"ticket_description": "Customer experiencing PostgreSQL performance issues with slow queries"}'
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     AWS Cloud (us-east-1)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌─────────────────────────────────┐ │
│  │   Streamlit  │         │     Lambda Function URL         │ │
│  │   Frontend   │────────▶│  (15-minute timeout support)    │ │
│  │ (ECS Fargate)│         └───────────────┬─────────────────┘ │
│  └──────────────┘                         │                    │
│         │                                 │                    │
│         │                    ┌────────────▼─────────────┐     │
│         └───────────────────▶│   Orchestration Lambda   │     │
│                              │  (Bedrock Agent Client)  │     │
│                              └────────────┬─────────────┘     │
│                                           │                    │
│                              ┌────────────▼─────────────┐     │
│                              │     Bedrock Agent        │     │
│                              │  (Claude Sonnet 4.5)     │     │
│                              └─────┬───────────┬────────┘     │
│                                    │           │               │
│                   ┌────────────────┘           └──────────┐   │
│                   │                                       │   │
│         ┌─────────▼────────┐              ┌──────────────▼─┐ │
│         │  Action Groups   │              │ Knowledge Bases│ │
│         │ ┌──────────────┐ │              │ ┌────────────┐ │ │
│         │ │   Zendesk    │ │              │ │  Tickets   │ │ │
│         │ │   Lambda     │ │              │ │   (OSS)    │ │ │
│         │ └──────────────┘ │              │ └────────────┘ │ │
│         │ ┌──────────────┐ │              │ ┌────────────┐ │ │
│         │ │    Slack     │ │              │ │FDE Profiles│ │ │
│         │ │   Lambda     │ │              │ │   (OSS)    │ │ │
│         │ └──────────────┘ │              │ └────────────┘ │ │
│         └──────────────────┘              └────────────────┘ │
│                                                               │
│         ┌───────────────────────────────────────────┐       │
│         │          S3 Data Bucket                   │       │
│         │  ┌──────────────┐  ┌──────────────────┐  │       │
│         │  │   tickets/   │  │  fde-profiles/   │  │       │
│         │  │   (CSV)      │  │     (CSV)        │  │       │
│         │  └──────────────┘  └──────────────────┘  │       │
│         └───────────────────────────────────────────┘       │
│                                                               │
└─────────────────────────────────────────────────────────────────┘

Legend:
OSS = OpenSearch Serverless (vector database)
All components created automatically by Terraform
```

## Resource Outputs

After deployment, Terraform provides comprehensive outputs:

```bash
# View all outputs
terraform output

# Specific outputs
terraform output frontend_url
terraform output lambda_function_url
terraform output -json bedrock_resources | jq
terraform output -json s3_data_bucket | jq
```

### Key Outputs

| Output | Description |
|--------|-------------|
| `frontend_url` | Streamlit application URL (http://alb-dns-name) |
| `lambda_function_url` | Direct Lambda URL (15-min timeout) |
| `bedrock_resources` | Agent ID, Alias IDs, KB IDs |
| `s3_data_bucket` | S3 bucket details for data upload |
| `deployment_summary` | High-level deployment information |

## Cost Estimate

Monthly costs for 100 tickets/month:

| Service | Usage | Cost |
|---------|-------|------|
| Bedrock Claude Sonnet 4.5 | 200K tokens | ~$0.60 |
| Bedrock Titan Embeddings | 50K tokens | ~$0.10 |
| OpenSearch Serverless | 2 collections | ~$1.50 |
| Lambda | 300 invocations | ~$0.05 |
| Lambda Function URL | 100 requests | $0.00 |
| ECS Fargate | 1 task (0.5 vCPU) | ~$3.00 |
| S3 | 1GB storage | ~$0.02 |
| ALB | Always-on | ~$16.00 |
| CloudWatch | Logs/metrics | ~$1.00 |
| **Total** | | **~$22.27/month** |

**Cost Optimization Tips:**
- Use Fargate Spot for ECS tasks (up to 70% savings)
- Implement ALB idle timeout to reduce costs
- Use S3 Intelligent-Tiering for data storage
- Set CloudWatch log retention policies

## Troubleshooting

### Issue: Terraform fails with "InvalidParameterException"

**Cause:** Bedrock models not enabled in your AWS account

**Solution:**
```bash
# Go to AWS Bedrock Console → Model access
# Enable: anthropic.claude-sonnet-4-5-20250929-v1:0
# Enable: amazon.titan-embed-text-v2:0
```

### Issue: Knowledge Base ingestion fails

**Cause:** Empty or incorrectly formatted CSV files

**Solution:**
```bash
# Check S3 bucket contents
aws s3 ls s3://$(terraform output -raw s3_data_bucket_name)/tickets/

# Verify CSV format (must have headers)
# Expected columns for tickets: ticket_id, subject, description, resolution, tags
# Expected columns for FDE profiles: name, email, expertise, certifications
```

### Issue: Lambda timeout errors

**Cause:** Bedrock Agent taking too long (>2 minutes)

**Solution:**
Already solved! Lambda Function URL supports 15-minute timeouts. Make sure your Streamlit frontend uses the Function URL, not API Gateway:

```bash
# Update frontend/.env
API_ENDPOINT=$(terraform output -raw lambda_function_url)
```

### Issue: Frontend shows 502 Bad Gateway

**Cause:** ECS task not healthy or ALB health check failing

**Solution:**
```bash
# Check ECS task status
aws ecs describe-services \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services $(terraform output -raw ecs_service_name)

# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw alb_target_group_arn)

# View ECS task logs
aws logs tail --follow /ecs/zendesk-sme-finder-frontend
```

## Maintenance & Updates

### Updating Bedrock Agent Instructions

```bash
# Edit the agent instructions
vim terraform/bedrock_agent.tf  # Update locals.agent_instructions

# Re-apply
terraform apply

# Agent will be automatically updated and prepared
```

### Adding New Data to Knowledge Bases

```bash
# Upload new CSV files
aws s3 cp new-tickets.csv s3://$(terraform output -raw s3_data_bucket_name)/tickets/

# Trigger re-ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $(terraform output -json bedrock_resources | jq -r '.tickets_kb_id') \
  --data-source-id $(terraform output -json bedrock_resources | jq -r '.tickets_data_source')
```

### Scaling ECS Frontend

```hcl
# Edit terraform.tfvars
ecs_desired_count = 2  # Increase for more capacity
ecs_max_capacity  = 4  # Auto-scaling limit

# Apply changes
terraform apply
```

## Cleanup

### Destroy All Resources

```bash
# WARNING: This will delete EVERYTHING
terraform destroy

# Confirm with: yes
```

### Selective Destruction

```bash
# Destroy only frontend
terraform destroy -target=aws_ecs_service.frontend

# Destroy only Bedrock Agent (keep Knowledge Bases)
terraform destroy -target=aws_bedrockagent_agent.fde_finder
```

## Comparison: Manual vs Automated

| Aspect | Manual Deployment | Automated (IaC) |
|--------|-------------------|-----------------|
| **Time** | 2-3 hours | 15 minutes |
| **Errors** | High (many console clicks) | Low (validated code) |
| **Reproducibility** | Difficult | Perfect |
| **Documentation** | Separate docs | Code is documentation |
| **Multi-Environment** | Repeat manually | `terraform workspace` |
| **Rollback** | Manual, error-prone | `terraform destroy` |
| **Version Control** | Not possible | Full Git history |
| **Team Collaboration** | Hard to share steps | Share Terraform code |
| **Cost Tracking** | Manual spreadsheet | `terraform show` |
| **Compliance** | Manual audits | Automated with Terraform Cloud |

## Benefits of IaC Automation

**Consistency** - Same infrastructure every time
**Speed** - 15 minutes vs 2-3 hours
**Reproducibility** - Multi-environment deployment
**Documentation** - Code is self-documenting
**Version Control** - Track all infrastructure changes
**Collaboration** - Team can review and contribute
**Safety** - Plan before apply, rollback capability
**Testing** - Test infrastructure changes in dev first
**Compliance** - Automated security and compliance checks

## Next Steps

1. Deploy with `terraform apply`
2. Upload your CSV data to S3
3. Trigger Knowledge Base ingestion
4. Test the Streamlit frontend
5. Monitor CloudWatch logs
6. Read [HYBRID_WORKFLOW_GUIDE.md](../HYBRID_WORKFLOW_GUIDE.md)
7. Read [COMPLETE_DEPLOYMENT_GUIDE.md](../COMPLETE_DEPLOYMENT_GUIDE.md)

## Support

For issues or questions:
- Check CloudWatch logs
- Run `terraform output post_deployment_instructions`
- Review this guide
- Check [TERRAFORM_DEPLOYMENT_GUIDE.md](./TERRAFORM_DEPLOYMENT_GUIDE.md)

---

**Built with Terraform + AWS Bedrock + Claude Sonnet 4.5**
