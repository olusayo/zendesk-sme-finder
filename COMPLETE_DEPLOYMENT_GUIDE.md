# Complete AWS Deployment Guide - Zendesk SME Finder
## Automated (Terraform) + Manual Deployment Options

⚡ **NEW: Fully Automated Deployment Available!**

**We now offer TWO deployment methods:**

### 🚀 Option 1: Fully Automated (Terraform) - **RECOMMENDED** ⭐
- **Time**: 15 minutes
- **Expertise**: Basic AWS CLI knowledge
- **Automation**: 95% automated via Infrastructure as Code
- **Guide**: See [terraform/IAC_AUTOMATION_GUIDE.md](terraform/IAC_AUTOMATION_GUIDE.md)
- **What's Automated**:
  - ✅ Bedrock Agent creation
  - ✅ Knowledge Bases with OpenSearch
  - ✅ Lambda functions & Function URLs
  - ✅ S3 buckets for data
  - ✅ ECS Fargate frontend
  - ✅ All IAM roles & policies
  - ✅ VPC, ALB, and networking

**Quick Start (Automated):**
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your credentials
terraform init
terraform apply -auto-approve
# Upload your data to S3 (paths in output)
# Done! ✅
```

### 📖 Option 2: Manual Deployment (This Guide)
- **Time**: 2-3 hours
- **Expertise**: None required - browser only
- **Automation**: Step-by-step console clicking
- **Best For**: Learning AWS services, understanding architecture

---

**✨ Updated for 2026**: This guide reflects the latest AWS console interface:
- Claude 4.5 model family (Sonnet 4.5, Opus 4.5, Haiku 4.5)
- Bedrock model access process with use case submission
- OpenSearch Serverless with "Vector search" type
- Enhanced Bedrock Agents console
- Lambda Function URLs (15-minute timeout support)
- Hybrid workflow (works without Zendesk/Slack API keys)

---

## What You're Building

**Zendesk Ticket SME Finder** - An intelligent system that helps CREs quickly find the right subject matter experts for complex support tickets.

### The Problem
CREs waste time manually searching for expertise when stuck on complex tickets, leading to delayed customer resolutions and knowledge silos.

### The Solution
An AI-powered routing system that:
- Analyzes ticket content using embeddings
- Compares against historical ticket resolutions
- Matches CRE certification profiles and past successful assignments
- Identifies the top 3 most relevant SMEs
- Facilitates introductions via Slack integration

### How It Works

```
User enters Ticket ID OR Description in Chat Interface
         ↓
Streamlit App (hosted on ECS Fargate)
         ↓
Lambda Function URL (15-minute timeout support)
         ↓
Orchestration Lambda Function (Hybrid Workflow)
         ↓
Bedrock Agent executes:
  1. Fetches ticket from Zendesk (if ticket_id provided) OR uses description
  2. Finds 3 similar resolved tickets (Knowledge Base 1)
  3. Finds 3 recommended FDEs with expertise reasoning (Knowledge Base 2)
  4. Creates Slack conversation (if ticket_id provided)
  5. Updates Zendesk ticket (if ticket_id provided)
         ↓
Results with FDE recommendations + reasoning displayed in Chat Interface
```

**New Features:**
- **Hybrid Workflow**: Works with OR without Zendesk/Slack API keys
- **Lambda Function URLs**: 15-minute timeout (vs 29-second API Gateway limit)
- **Expertise Reasoning**: Detailed explanations for each FDE recommendation
- **Flexible Input**: Ticket ID or natural language description

---

## Table of Contents

### Quick Start Path (Get Streamlit Running First!)
1. [Before You Begin](#before-you-begin)
2. [Part 1: AWS Account Setup](#part-1-aws-account-setup)
3. [Part 2: Gather Required Credentials](#part-2-gather-required-credentials)
4. [Part 3: CloudShell Setup](#part-3-cloudshell-setup)
5. [Part 4: Configure AWS Bedrock](#part-4-configure-aws-bedrock)
6. **[Part 5: Deploy Infrastructure with Terraform](#part-5-deploy-infrastructure-with-terraform)** ← Start Here to See Your App!
7. **[Part 6: Build and Deploy Frontend](#part-6-build-and-deploy-frontend)** ← See Streamlit Running!

### Complete AI Integration
8. [Part 7: Create Knowledge Bases](#part-7-create-knowledge-bases)
9. [Part 8: Create Bedrock Agent](#part-8-create-bedrock-agent)
10. [Part 9: Update and Redeploy](#part-9-update-and-redeploy)
11. [Part 10: Testing Your Deployment](#part-10-testing-your-deployment)
12. [Part 11: Monitoring](#part-11-monitoring)
13. [Part 12: Cleanup](#part-12-cleanup)
14. [Troubleshooting](#troubleshooting)

---

## Before You Begin

### What You Need

1. Web browser (Chrome, Firefox, Safari, or Edge)
2. Email address
3. Credit/debit card (for AWS account verification)
4. Zendesk account with admin access
5. Slack workspace with admin access
6. 60-90 minutes of uninterrupted time

### What You'll Build

- AI-powered FDE finder with chat interface
- Fully automated infrastructure on AWS ECS Fargate
- Scalable, production-ready deployment
- Automated Slack and Zendesk integrations

### Cost Expectations

**Development/Testing**:
- Most services covered by AWS Free Tier
- Estimated: $0-10/month for light testing

**Production**:
- ~$115/month (ECS Fargate, ALB, NAT Gateways, Lambda)
- Can delete everything after testing to avoid charges

---

## Part 1: AWS Account Setup

### Step 1.1: Create AWS Account

1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Enter email address and account name
4. Click "Verify email address"
5. Check email for verification code
6. Enter the 6-digit code and click "Verify"

### Step 1.2: Create Password

1. Create strong password (8+ characters, uppercase, lowercase, numbers, symbols)
2. Confirm password
3. Click "Continue"

### Step 1.3: Add Contact Information

1. Select account type (Personal or Business)
2. Fill in contact information
3. Check "AWS Customer Agreement" box
4. Click "Continue"

### Step 1.4: Add Payment Information

1. Enter credit/debit card information
2. Click "Verify and Add"
3. AWS will charge $1 for verification (refunded)

### Step 1.5: Confirm Identity

1. Choose verification method (SMS or Voice call)
2. Enter phone number
3. Enter verification code received
4. Click "Continue"

### Step 1.6: Choose Support Plan

1. Select "Basic support - Free"
2. Click "Complete sign up"
3. Wait for confirmation (can take a few minutes)
4. Click "Go to the AWS Management Console"

### Step 1.7: Sign In

1. Enter root user email
2. Click "Next"
3. Enter password
4. Click "Sign in"

You're now in the AWS Console!

---

## Part 2: Gather Required Credentials

Before deploying, collect these credentials. Keep them in a text file temporarily.

### Step 2.1: Zendesk API Credentials

1. Log in to your Zendesk account
2. Click the gear icon (Admin)
3. Go to "Apps and integrations" → "APIs" → "Zendesk API"
4. Under "Settings", enable "Token Access"
5. Click the "+" button to add a new API token
6. Description: "FDE Finder Integration"
7. Copy the token immediately (you won't see it again)
8. Save in your text file as:
   ```
   Zendesk Domain: yourcompany.zendesk.com
   Zendesk Email: your-email@company.com
   Zendesk API Token: [paste token]
   ```

### Step 2.2: Slack Bot Token

1. Go to https://api.slack.com/apps
2. Click "Create New App"
3. Choose "From scratch"
4. App Name: "FDE Finder Bot"
5. Select your workspace
6. Click "Create App"

**Configure Bot Permissions**:
7. In left sidebar, click "OAuth & Permissions"
8. Scroll to "Scopes" → "Bot Token Scopes"
9. Add these scopes:
   - `chat:write`
   - `channels:manage`
   - `channels:read`
   - `users:read`
   - `users:read.email`

**Install to Workspace**:
10. Scroll up to "OAuth Tokens"
11. Click "Install to Workspace"
12. Click "Allow"
13. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
14. Save in your text file as:
    ```
    Slack Bot Token: xoxb-...
    Slack Team URL: https://yourteam.slack.com
    ```

---

## Part 3: CloudShell Setup

### Step 3.1: Open CloudShell

1. In AWS Console, click the CloudShell icon (looks like `>_` in top navigation bar)
2. Wait for CloudShell to initialize (30-60 seconds)
3. You'll see a command prompt like: `[cloudshell-user@ip-xxx ~]$`

### Step 3.2: Clone the Repository

In CloudShell, run these commands one at a time:

```bash
cd ~
```

Press Enter.

**Remove any existing clone** (if you previously cloned):

```bash
rm -rf git-repository
```

Press Enter.

**Clone the repository**:

```bash
git clone https://github.com/olusayo/git-repository.git
```

Press Enter. Wait for the clone to complete (~10 seconds).

**Important**: Check out the correct branch and navigate to the project:

```bash
cd git-repository/other_projects
git checkout oakinlaja_UPDATES
git pull origin oakinlaja_UPDATES
cd Zendesk_SME_Finder
```

Press Enter after each command.

### Step 3.4: Verify Files

```bash
ls
```

Press Enter.

You should see directories like:
- `frontend`
- `lambdas`
- `terraform`
- `docs`

And files like:
- `README.md`
- `COMPLETE_DEPLOYMENT_GUIDE.md`

### Step 3.5: Verify Terraform

CloudShell has Terraform pre-installed. Verify:

```bash
terraform version
```

Press Enter.

You should see `Terraform v1.5.x` or higher.

---

## Part 4: Configure AWS Bedrock

**🎉 Major Update (2026)**: AWS has **simplified model access**! Foundation models are now automatically enabled when first invoked - no manual activation required! However, Anthropic models still need a one-time use case submission.

### Step 4.1: Navigate to Bedrock Console

1. Sign in to the AWS Management Console
2. In the search bar at the top, type: **`Bedrock`**
3. Click **"Amazon Bedrock"** from the dropdown results
4. **Important**: Make sure you're in the **us-east-1 (N. Virginia)** region (check top-right corner)

### Step 4.2: Understanding the New Model Access Process

**What Changed**:
- ✅ **Model access page has been retired**
- ✅ **Serverless foundation models are now automatically enabled** across all AWS commercial regions when first invoked
- ✅ **No manual activation needed** - models are instantly available
- ⚠️ **Exception**: Anthropic models require a one-time use case submission for first-time users

**What This Means for You**:
- Claude Sonnet 4.5 and Titan Embeddings will be automatically enabled when your Lambda functions invoke them
- You only need to submit use case details for Anthropic models (one-time setup)

### Step 4.3: Submit Anthropic Use Case Details (Required)

Since this is likely your first time using Anthropic Claude models, you need to submit use case details once.

1. In the **left navigation pane**, click **"Foundation models"**
2. Click **"Model catalog"**
3. In the model catalog, find and click on **"Anthropic"** section
4. Click on **"Claude Sonnet 4.5"** (or latest Claude 4.5 model available)
5. You'll see a button to **"Submit use case details"** or **"Request access"**
6. Click the button to open the use case form

7. **Fill in the use case form**:
   - **Use case name**: `Zendesk SME Finder`
   - **Use case description**: `AI agent to match support engineers with field development experts for complex tickets using RAG and knowledge bases`
   - **Industry**: Select your industry (e.g., "Technology", "Software & Internet", "Information Technology")
   - **Use case type**: Select "Internal tool" or "Business application"

8. Click **"Submit"**
9. You should see a confirmation: **"Use case submitted successfully"**
   - Access is granted **immediately** after submission

### Step 4.4: Verify Model Availability (Optional)

To confirm models are ready:

1. Stay in the **Model catalog**
2. Search for **"Claude Sonnet 4.5"** - should show as available
3. Search for **"Titan Text Embeddings"** - should show as available

**That's it!** No need to manually enable models - they're automatically available when invoked.

### Troubleshooting

**If you see "Model access denied" when testing later**:
- Verify you submitted the Anthropic use case (Step 4.3)
- Ensure your IAM role has `bedrock:InvokeModel` permission
- Check that you're in the **us-east-1** region
- For Marketplace models, someone with Marketplace permissions must invoke it once

**If you can't find the Model catalog**:
- Look in the left navigation under **"Foundation models"**
- Ensure you're in the correct region (us-east-1)
- Refresh your browser

**If use case submission fails**:
- Ensure all required fields are filled out
- Try a different browser or clear cache
- Wait 5 minutes and try again
- Check you have Marketplace permissions enabled in your account

### New Model Access Architecture

**How It Works Now**:
```
First API Call → Anthropic Model
         ↓
   Check: Use case submitted?
         ↓
    Yes → Model invokes successfully ✅
    No  → Error: Submit use case ❌
```

**For Amazon Models** (Titan Embeddings):
```
First API Call → Amazon Model
         ↓
   Automatically enabled ✅
         ↓
   Model invokes successfully
```

### Additional Resources

- [Bedrock Model Access Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
- [Model Catalog](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html)
- [IAM Permissions for Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html)

---

## Part 5: Deploy Infrastructure with Terraform

🚀 **This is where the magic happens!** After this step, you'll have your Streamlit app running on AWS!

This deploys:
- **ECS Fargate cluster** - Where your Streamlit app will run
- **Application Load Balancer** - Public endpoint for your app
- **VPC with networking** - Secure infrastructure
- **Lambda functions** - Backend AI processing
- **API Gateway** - RESTful API
- All supporting infrastructure

**Time required**: 10-12 minutes

### Step 5.1: Navigate to Terraform Directory

In CloudShell:

```bash
cd ~/git-repository/other_projects/Zendesk_SME_Finder/terraform
```

Press Enter.

### Step 5.2: Create Configuration File

```bash
cp terraform.tfvars.example terraform.tfvars
```

Press Enter.

```bash
nano terraform.tfvars
```

Press Enter.

### Step 5.3: Fill in Your Credentials

Use arrow keys to move cursor. Edit these values (use credentials from Part 2):

```hcl
# AWS Configuration
aws_region = "us-east-1"

# Zendesk Configuration
zendesk_domain    = "yourcompany.zendesk.com"
zendesk_email     = "your-email@company.com"
zendesk_api_token = "paste-your-zendesk-token-here"

# Slack Configuration
slack_bot_token = "xoxb-paste-your-slack-token-here"
slack_team_url  = "https://yourteam.slack.com"

# Bedrock Agent (leave empty for now)
bedrock_agent_id       = ""
bedrock_agent_alias_id = ""

# S3 Configuration (use existing buckets or leave as-is)
tickets_s3_bucket       = "genai-enablement-team3"
tickets_s3_prefix       = "tickets/"
certificates_s3_bucket  = "genai-enablement-team3"
certificates_s3_prefix  = "certificates/"
```

### Step 5.4: Save the File

1. Press `Ctrl + X`
2. Press `Y`
3. Press `Enter`

### Step 5.5: Initialize Terraform

```bash
terraform init
```

Press Enter.

Wait for completion (~30 seconds). You should see:
```
Terraform has been successfully initialized!
```

### Step 5.6: Preview Deployment

```bash
terraform plan
```

Press Enter.

Review the output. You should see:
```
Plan: 59 to add, 0 to change, 0 to destroy.
```

This includes:
- 17 Lambda/API Gateway resources
- 42 ECS/VPC/Networking resources

### Step 5.7: Deploy Infrastructure

```bash
terraform apply
```

Press Enter.

When prompted:
```
Do you want to perform these actions?
```

Type: `yes`

Press Enter.

Wait 8-12 minutes for deployment.

You'll see progress messages like:
- Creating VPC...
- Creating subnets...
- Creating Lambda functions...
- Creating ECS cluster...
- Creating load balancer...

### Step 5.8: Save Terraform Outputs

When complete, save these outputs:

```bash
terraform output -json | jq
```

Press Enter.

Copy and save these values to your text file:
- `api_gateway_endpoint`
- `ecr_repository_url`
- `ecs_cluster_name`
- `ecs_service_name`
- `bedrock_agent_role_arn` (needed for Part 8)

**Get API Key** (sensitive value):
```bash
terraform output -raw api_key
```

Press Enter. Copy and save this value.

---

## Part 6: Build and Deploy Frontend

🎉 **Almost there! This is the final step to see your Streamlit app running!**

Now build the Docker image for the beautiful Streamlit chat interface and deploy to ECS.

**Time required**: 8-10 minutes (includes Docker installation)

### Step 6.1: Install Docker in CloudShell

CloudShell doesn't have Docker pre-installed, so we need to install it first.

```bash
cd ~/git-repository/other_projects/Zendesk_SME_Finder/terraform
```

Press Enter.

```bash
chmod +x install-docker-cloudshell.sh
./install-docker-cloudshell.sh
```

Press Enter. Wait for Docker to install (~2 minutes).

### Step 6.2: Activate Docker Group

After Docker installs, run this command to activate Docker without logging out:

```bash
newgrp docker
```

Press Enter. This reloads your shell with Docker permissions.

### Step 6.3: Run Build Script

Now build and push the Docker image:

```bash
cd ~/git-repository/other_projects/Zendesk_SME_Finder/terraform
chmod +x build-and-push-frontend.sh
./build-and-push-frontend.sh
```

Press Enter.

The script will:
1. Authenticate Docker to ECR
2. Build the Streamlit Docker image
3. Tag with `latest` and timestamp
4. Push to ECR repository
5. Trigger ECS deployment

Wait 3-5 minutes for build and push.

You'll see output like:
```
Building Docker image...
Successfully built abc123def456
Pushing image to ECR...
Success!
```

### Step 6.4: Wait for ECS Deployment

Wait 2-3 minutes for ECS to:
- Pull the Docker image
- Start the task
- Register with load balancer
- Pass health checks

Check status:
```bash
aws ecs describe-services \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services $(terraform output -raw ecs_service_name) \
  --query 'services[0].runningCount'
```

When you see `1`, the service is running.

### Step 6.5: Get Frontend URL

```bash
terraform output -raw frontend_url
```

Press Enter.

Example output:
```
http://zendesk-sme-finder-alb-123456789.us-east-1.elb.amazonaws.com
```

Copy this URL. Open it in a new browser tab.

🎊 **Congratulations!** You should see the beautiful Streamlit chat interface with:
- Professional dark blue and charcoal color scheme
- Clean, modern typography
- Welcome message from the FDE Finder assistant

**What you can do now**:
- ✅ See the beautiful interface running
- ✅ Type messages in the chat (UI will respond)
- ❌ Full AI functionality requires completing Parts 7-9 (Bedrock Agent setup)

**Want to try it out?** Type "Find FDEs for ticket 12345" to see the chat interaction (full results come after Part 9).

**Ready for full AI power?** Continue to Part 7 to enable Knowledge Bases and Bedrock Agent!

---

## Part 7: Create Knowledge Bases

Knowledge Bases allow the AI to search historical tickets and FDE profiles using vector embeddings.

**Console Navigation Note**: In the current AWS Bedrock console (2025-2026), "Knowledge bases" and "Agents" are located in the left navigation pane, typically under a section called "Builder tools". If you don't see these options, ensure you're in the correct region (us-east-1) and have the necessary permissions.

### Step 7.1: Skip Manual OpenSearch Setup (2026 Simplified Process)

**🎉 Good News**: In the 2026 AWS console, you no longer need to manually create OpenSearch collections! AWS Bedrock will automatically create and configure everything when you create the Knowledge Base.

**What Changed**:
- ✅ The **"Quick create a new vector store"** option automatically creates OpenSearch collections, indexes, and all required configurations
- ✅ No need to manually create data access policies
- ✅ No need to copy/paste collection endpoints
- ✅ Everything is handled automatically by AWS

**Skip to Step 7.2** to create your first Knowledge Base. AWS will handle all the OpenSearch setup for you!

### Step 7.2: Create Similar Tickets Knowledge Base

1. In AWS Console search bar, type **"Bedrock"**
2. Click **"Amazon Bedrock"**
3. In the **left navigation pane**, find and click **"Knowledge bases"**
   - Note: Knowledge bases may be under a section called **"Builder tools"**
4. Click the orange **"CREATE"** button (2026 console update)
5. From the dropdown menu, select **"Knowledge Base with Vector Store"**
   - This option uses vector databases like OpenSearch Serverless for semantic search

**Knowledge Base Details**:
6. Name: `similar-tickets-kb`
7. Description: "Historical resolved tickets for similarity matching"
8. IAM role: "Create and use a new service role"
9. Click "Next"

**Configure Data Source**:
10. **Data source name**: `tickets-s3-data`
11. **Data source type**: Should be "S3" (default)
12. **S3 URI**: `s3://genai-enablement-team3/tickets/`
13. **Chunking strategy**: Leave as default (Fixed-size chunking recommended)
14. **Max tokens**: Leave as default (300 is typical)
15. **Overlap percentage**: Leave as default (20% is typical)
16. Click "Next"

**Configure Embeddings and Vector Store** (2026 Console - Simplified):
17. **Embeddings model**: Select **"Titan Text Embeddings V2"** (or "Titan Embeddings G1 - Text")
   - Note: V2 is newer and recommended if available
18. **Vector store**: Select **"OpenSearch Serverless"**
19. ⚠️ **IMPORTANT**: Select **"Quick create a new vector store - Recommended"** (the top radio button)
   - This will automatically create an OpenSearch collection, index, and all configurations
   - AWS will handle naming and setup automatically
   - No need to provide collection endpoints or index names

20. Click "Next"

**Review and Create**:
21. Review your settings
22. Click "Create knowledge base"
23. Wait 2-3 minutes for creation
   - AWS will automatically create the OpenSearch collection and index in the background

**Sync Data**:
24. Once creation completes, click the "Sync" button
25. Wait 5-10 minutes for sync to complete
26. Status will change from "Syncing" to "Available"
25. Status will change to "Available"

**Save Knowledge Base ID**:
26. Copy the "Knowledge base ID" (looks like: `ABCDEFGH12`)
27. Save it as "Similar Tickets KB ID"

### Step 7.3: Create FDE Profiles Knowledge Base

Repeat Step 7.2 for FDE profiles:

1. Click the orange **"CREATE"** button
2. Select **"Knowledge Base with Vector Store"**
3. **Name**: `fde-profiles-kb`
4. **Description**: "FDE certification profiles and expertise"
5. **IAM role**: "Create and use a new service role"
6. Click "Next"

**Configure Data Source**:
7. **Data source name**: `fde-s3-data`
8. **Data source type**: "S3"
9. **S3 URI**: `s3://genai-enablement-team3/certificates/`
10. **Chunking strategy**: Leave as default
11. **Max tokens**: Leave as default
12. **Overlap percentage**: Leave as default
13. Click "Next"

**Configure Embeddings and Vector Store**:
14. **Embeddings model**: "Titan Text Embeddings V2" (or "Titan Embeddings G1 - Text")
15. **Vector store**: "OpenSearch Serverless"
16. Select **"Quick create a new vector store - Recommended"**
   - AWS will automatically create a separate OpenSearch collection for FDE profiles
17. Click "Next"

**Review and Create**:
18. Review settings and click "Create knowledge base"
19. Wait 2-3 minutes for creation

**Sync Data**:
20. Click "Sync" button
21. Wait 5-10 minutes for sync to complete
22. Status will change to "Available"
23. **Save "Knowledge base ID"** as "FDE Profiles KB ID"

---

## Part 8: Create Bedrock Agent

The Bedrock Agent orchestrates everything.

### Step 8.1: Navigate to Agents

1. In AWS Console search bar, type **"Bedrock"** and click **"Amazon Bedrock"**
2. In the **left navigation pane**, find and click **"Agents"**
   - Note: Agents may be under a section called **"Builder tools"** or **"Orchestration"**
3. Click the orange **"Create Agent"** button

### Step 8.2: Configure Agent

**Provide Agent Details**:
1. **Agent name**: `zendesk-sme-finder-agent`
2. **Agent description**: `AI agent for finding FDEs to help with Zendesk tickets`
3. Click the orange **"Create"** button
   - Note: In the 2026 console, the "User input" option has been removed - agents now accept user input by default

**Select Foundation Model** (Updated for 2026):
5. In the **"Agent builder"** page, find the **"Select model"** section
6. Click **"Edit"** or the model selection dropdown
7. **Model provider**: Select **"Anthropic"**
8. **Model**: Select **"Claude Sonnet 4.5"** (or latest Claude 4.5 model available)
   - Note: Claude Sonnet 4.5 offers excellent balance of performance and cost
   - If Claude Opus 4.5 is available and you need maximum capability, you can select that instead
9. Click **"Save"**

**Configure IAM Service Role**:
10. Scroll to the **"Permissions"** or **"Service role"** section
11. Click **"Edit"** next to the service role
12. Select **"Use an existing service role"**
13. From the dropdown, select: `zendesk-sme-finder-bedrock-agent-role` (this was created by Terraform)
14. Click **"Save"**

**Add Agent Instructions**:
15. Scroll to the **"Instructions"** section
16. Click **"Edit"**
17. Paste these instructions in the text box:

```
You are an AI assistant that helps CREs find the right Field Development Engineers (FDEs) for complex Zendesk support tickets.

Your workflow:
1. When given a ticket ID, fetch the full ticket details from Zendesk
2. Search the similar-tickets knowledge base for 3 historically similar tickets that were successfully resolved
3. Search the fde-profiles knowledge base for 3 FDEs whose expertise best matches the ticket requirements
4. Create a Slack conversation including the assigned engineer and the 3 recommended FDEs
5. Update the Zendesk ticket with the Slack conversation link and FDE recommendations

Always:
- Analyze ticket content, tags, and complexity
- Match FDE expertise to ticket requirements
- Calculate confidence scores (0.0-1.0) for each recommendation
- Include reasoning for each FDE match
- Provide similar ticket summaries with resolution details
- If overall confidence is low (< 0.6), mention this in the response
- Handle errors gracefully
- Ensure the Slack conversation includes all necessary ticket context
- Always call updateTicket after creating the Slack conversation
```

18. Click **"Save"**

### Step 8.3: Add Action Groups

**Note**: Action groups connect the Bedrock Agent to your Lambda functions. The 2026 console has improved schema editors.

**Add Zendesk Action Group**:

1. Scroll down to the **"Action groups"** section
2. Click **"Add"** button
3. **Action group name**: `zendesk-operations`
4. **Description**: "Fetch and update Zendesk tickets"
5. **Action group type**: Select **"Define with API schemas"**
6. **Action group executor**:
   - Select **"Select an existing Lambda function"**
   - From dropdown, choose: `zendesk-sme-finder-zendesk-actions`
7. **Action group schema**:
   - Select **"Define with in-line OpenAPI schema editor"**
8. Click in the **OpenAPI schema editor** box
9. Paste this schema:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Zendesk Operations API",
    "version": "1.0.0",
    "description": "Fetch and update Zendesk tickets"
  },
  "paths": {
    "/fetchTicket": {
      "post": {
        "summary": "Fetch ticket details from Zendesk",
        "description": "Retrieves complete ticket information including subject, description, tags, and assigned engineer",
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
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "assigned_engineer": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/updateTicket": {
      "post": {
        "summary": "Update Zendesk ticket with FDE recommendations",
        "description": "Adds internal note to ticket with Slack link and recommended FDEs",
        "operationId": "updateTicket",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "ticket_id": {"type": "string"},
                  "slack_url": {"type": "string"},
                  "recommended_fdes": {"type": "array"}
                },
                "required": ["ticket_id"]
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

10. Scroll down and click the **"Add"** or **"Create"** button to save this action group

**Add Slack Action Group**:

11. In the Action groups section, click **"Add"** again to create a second action group
12. **Action group name**: `slack-operations`
13. **Description**: "Create Slack conversations"
14. **Action group type**: **"Define with API schemas"**
15. **Action group executor**: Select **"Select an existing Lambda function"**
16. **Lambda function**: Choose `zendesk-sme-finder-slack-actions` from dropdown
17. **Action group schema**: Select **"Define with in-line OpenAPI schema editor"**
18. Paste this schema:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Slack Operations API",
    "version": "1.0.0",
    "description": "Create Slack conversations"
  },
  "paths": {
    "/createConversation": {
      "post": {
        "summary": "Create Slack conversation",
        "description": "Creates channel and invites engineer and FDEs",
        "operationId": "createConversation",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "ticket_id": {"type": "string"},
                  "engineer_email": {"type": "string"},
                  "fde_emails": {"type": "array", "items": {"type": "string"}},
                  "ticket_summary": {"type": "string"}
                },
                "required": ["ticket_id", "engineer_email", "fde_emails"]
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
                    "slack_url": {"type": "string"}
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

19. Click the **"Add"** or **"Create"** button to save this action group

### Step 8.4: Add Knowledge Bases

Now connect your Knowledge Bases to the agent so it can search historical data.

1. Scroll to the **"Knowledge bases"** section
2. Click the **"Add"** button
3. From the dropdown, select: `similar-tickets-kb`
4. **Instructions for this knowledge base**:
   ```
   Use this knowledge base to find historically similar tickets and successful resolutions. Search for tickets that match the current ticket's content, tags, and problem description.
   ```
5. Click **"Add"**

6. Click **"Add"** again to add the second knowledge base
7. Select: `fde-profiles-kb`
8. **Instructions for this knowledge base**:
   ```
   Use this knowledge base to find FDEs with relevant expertise and experience. Search for FDEs whose skills, certifications, and past work match the current ticket's requirements.
   ```
9. Click **"Add"**

### Step 8.5: Save and Prepare Agent

**Important**: You must "Prepare" the agent to compile all configurations.

1. Scroll to the top of the page
2. Click the orange **"Save and exit"** or **"Save"** button
3. Wait for the save operation to complete (status will show at top)
4. Click the **"Prepare"** button (orange button near the top)
5. Wait 2-3 minutes for preparation to complete
6. You should see a success message: **"Agent prepared successfully"**
7. The agent version will be created (e.g., "Version 1")

**Note**: Every time you make changes to the agent, you must "Prepare" it again to apply the changes.

### Step 8.6: Test Agent (Optional but Recommended)

Before creating an alias, test the agent to ensure it works correctly.

1. On the right side of the page, find the **"Test"** panel or click **"Test agent"**
2. In the test chat interface, type: `Find FDEs for ticket 12345`
3. Click **"Run"** or press Enter
4. Wait 30-60 seconds for the agent to process
5. Review the agent's response - you should see it:
   - Fetching ticket details
   - Searching knowledge bases
   - Recommending FDEs
   - Creating Slack conversation

**If you see errors**, check:
- ✅ Knowledge Bases show "Available" status and are synced
- ✅ Lambda functions exist: `zendesk-sme-finder-zendesk-actions` and `zendesk-sme-finder-slack-actions`
- ✅ IAM role `zendesk-sme-finder-bedrock-agent-role` has correct permissions
- ✅ Agent was prepared successfully

### Step 8.7: Create Agent Alias

An alias allows you to reference a specific version of your agent in production.

1. At the top of the page, click **"Create alias"** or find **"Aliases"** tab
2. **Alias name**: `production`
3. **Description**: `Production version of FDE Finder`
4. **Agent version**: Select the version you just prepared (e.g., "Version 1" or "DRAFT")
5. Click **"Create alias"**
6. Wait for creation to complete (~30 seconds)

**Save Agent IDs** (Critical - You'll need these for Terraform):

7. Go back to the agent's main page
8. At the top, find and copy the **"Agent ID"** (looks like: `ABCDEFGHIJ`)
   - Save this as **"Agent ID"**
9. Click on the **"Aliases"** tab or find your `production` alias
10. Copy the **"Alias ID"** (looks like: `TSTALIASID` or similar)
    - Save this as **"Agent Alias ID"**

**Reference**: [Add action groups to your agent](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-add.html)

---

## Part 9: Update and Redeploy

Now update Terraform with the Agent IDs and redeploy.

### Step 9.1: Edit Terraform Variables

In CloudShell:

```bash
cd ~/git-repository/other_projects/Zendesk_SME_Finder/terraform
```

Press Enter.

```bash
nano terraform.tfvars
```

Press Enter.

### Step 9.2: Add Agent IDs

Find these lines:

```hcl
bedrock_agent_id       = ""
bedrock_agent_alias_id = ""
```

Replace with your actual IDs:

```hcl
bedrock_agent_id       = "ABCD1234EF"
bedrock_agent_alias_id = "TSTALIASID"
```

### Step 9.3: Save

1. Press `Ctrl + X`
2. Press `Y`
3. Press `Enter`

### Step 9.4: Apply Update

```bash
terraform apply
```

Press Enter.

Type: `yes`

Press Enter.

Wait ~30 seconds. This updates the Orchestration Lambda with Agent IDs.

The ECS service will automatically restart with the new configuration.

---

## Part 10: Testing Your Deployment

### Step 10.1: Access Frontend

Get your frontend URL:

```bash
terraform output -raw frontend_url
```

Press Enter.

Open the URL in your browser.

### Step 10.2: Test Chat Interface

You'll see the chat interface with a welcome message.

**Test the system**:

1. In the chat input box, type:
   ```
   Find FDEs for ticket 12345
   ```

2. Press Enter

3. Wait 30-90 seconds

4. The assistant will display:
   - Recommended FDEs (with confidence scores)
   - Similar resolved tickets
   - Slack conversation link
   - Zendesk ticket link

**Example response**:
```
✅ Found FDEs for ticket #12345

👥 Recommended Field Development Engineers

1. John Doe - 95% Match
   - Email: john.doe@company.com
   - Expertise: Kubernetes, AWS, Python
   - Slack: @johndoe

2. Jane Smith - 87% Match
   - Email: jane.smith@company.com
   - Expertise: Docker, CI/CD, Monitoring
   - Slack: @janesmith

...

🔗 Next Steps

✅ Open Slack Conversation
✅ View Zendesk Ticket

---

Need help with another ticket? Just let me know the ticket number!
```

### Step 10.3: Verify Slack Integration

1. Open your Slack workspace
2. Look for a new channel (named with ticket ID)
3. Verify the bot posted ticket information
4. Verify engineer and FDEs were invited

### Step 10.4: Verify Zendesk Integration

1. Log in to Zendesk
2. Open the ticket you tested
3. Check ticket comments
4. You should see an internal note with:
   - FDE recommendations
   - Slack conversation link
   - Confidence scores

### Step 10.5: Check Logs (If Issues)

In CloudShell:

```bash
aws logs tail /ecs/zendesk-sme-finder-frontend --follow
```

Or check Lambda logs:

```bash
aws logs tail /aws/lambda/zendesk-sme-finder-orchestration --follow
```

Press `Ctrl + C` to stop tailing logs.

---

## Part 11: Monitoring

### View ECS Service Status

```bash
aws ecs describe-services \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services $(terraform output -raw ecs_service_name)
```

### View Running Tasks

```bash
aws ecs list-tasks \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service-name $(terraform output -raw ecs_service_name)
```

### Check Frontend Logs

```bash
aws logs tail /ecs/zendesk-sme-finder-frontend --since 1h
```

### Check Cost

1. In AWS Console, search for "Billing"
2. Click "Billing and Cost Management"
3. Click "Bills"
4. Review current month charges

Set up billing alerts:
1. Click "Budgets"
2. Click "Create budget"
3. Type: Cost budget
4. Amount: $20
5. Email: your email
6. Create

---

## Part 12: Cleanup

To delete everything and avoid charges:

### Step 12.1: Destroy Terraform Resources

In CloudShell:

```bash
cd ~/git-repository/other_projects/Zendesk_SME_Finder/terraform
```

Press Enter.

```bash
terraform destroy
```

Press Enter.

Type: `yes`

Press Enter.

Wait 10-15 minutes. This deletes:
- ECS cluster and service
- Load balancer
- VPC and networking
- Lambda functions
- API Gateway
- Secrets Manager
- CloudWatch logs
- ECR repository

### Step 12.2: Delete Bedrock Agent

1. Go to Amazon Bedrock → Agents
2. Select `zendesk-sme-finder-agent`
3. Click "Delete"
4. Type: `delete`
5. Click "Delete"

### Step 12.3: Delete Knowledge Bases

1. Go to Bedrock → Knowledge bases
2. Select `similar-tickets-kb`
3. Click "Delete"
4. Confirm
5. Repeat for `fde-profiles-kb`

### Step 12.4: Delete OpenSearch Collections

1. Go to OpenSearch Service → Collections
2. Select `similar-tickets-vectors`
3. Click "Delete"
4. Type: `delete`
5. Confirm
6. Repeat for `fde-profiles-vectors`

### Step 12.5: Verify Cleanup

Check these services are empty:
- Lambda (no functions)
- ECS (no clusters)
- API Gateway (no APIs)
- VPC (no custom VPCs)
- CloudWatch (log groups may remain - delete if needed)

---

## Troubleshooting

### Frontend Not Loading

**Issue**: Browser shows error or blank page

**Solutions**:
1. Wait 2-3 minutes for ECS task to fully start
2. Check ECS service has running tasks:
   ```bash
   aws ecs describe-services \
     --cluster $(terraform output -raw ecs_cluster_name) \
     --services $(terraform output -raw ecs_service_name) \
     --query 'services[0].runningCount'
   ```
3. Check ALB health checks:
   ```bash
   aws elbv2 describe-target-health \
     --target-group-arn $(aws elbv2 describe-target-groups \
       --names zendesk-sme-finder-tg \
       --query 'TargetGroups[0].TargetGroupArn' \
       --output text)
   ```

### Chat Not Responding

**Issue**: Type ticket ID but no response

**Solutions**:
1. Check Bedrock Agent IDs are set in `terraform.tfvars`
2. Verify Bedrock models have "Access granted"
3. Check CloudWatch logs:
   ```bash
   aws logs tail /aws/lambda/zendesk-sme-finder-orchestration --follow
   ```

### "No FDEs Found"

**Issue**: Agent responds but no FDEs

**Solutions**:
1. Verify Knowledge Bases are synced
2. Check S3 buckets have data
3. Verify OpenSearch collections are active
4. Check data access policies in OpenSearch

### Terraform Errors

**Issue**: `terraform apply` fails

**Solutions**:
1. Run `terraform validate` to check syntax
2. Ensure AWS credentials are valid
3. Check quotas: ECS, Fargate, VPC limits
4. Review error message and fix configuration

### Build Script Fails

**Issue**: `./build-and-push-frontend.sh` errors

**Solutions**:
1. Ensure you ran `terraform apply` first
2. Check Docker is available (should be in CloudShell)
3. Verify ECR repository exists:
   ```bash
   aws ecr describe-repositories --repository-names zendesk-sme-finder-frontend
   ```

---

## Next Steps

After successful deployment:

1. **Test with real tickets**: Use actual Zendesk ticket IDs
2. **Train your team**: Share the frontend URL
3. **Monitor costs**: Set up billing alerts
4. **Customize**: Update agent instructions as needed
5. **Scale**: Increase `ecs_max_capacity` if needed

---

## Additional Resources

- [ECS Deployment Guide](terraform/ECS_DEPLOYMENT_GUIDE.md) - Detailed ECS documentation
- [Chat Interface Guide](frontend/CHAT_INTERFACE.md) - Chat features and customization
- [Validation Report](terraform/ECS_VALIDATION_REPORT.md) - Security and best practices
- [Terraform Summary](terraform/TERRAFORM_SUMMARY.md) - Quick reference

---

## Support

For issues:
- Check CloudWatch logs
- Review [Troubleshooting](#troubleshooting) section
- Check [ECS Validation Report](terraform/ECS_VALIDATION_REPORT.md)

**Total Deployment Time**: 60-90 minutes

**Congratulations! You've deployed an AI-powered SME Finder system!**
