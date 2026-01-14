# Terraform Deployment Guide - Zendesk SME Finder

This guide shows you how to deploy the Zendesk SME Finder infrastructure using Terraform. This is much faster and more reliable than manual deployment.

## What Terraform Will Deploy

Terraform will automatically create:

- IAM roles and policies for Lambda functions and Bedrock Agent
- AWS Secrets Manager secrets for Zendesk and Slack credentials
- 3 Lambda functions (Zendesk actions, Slack actions, Orchestration)
- API Gateway with REST API endpoint
- API Key and Usage Plan
- CloudWatch Log Groups for monitoring

## What You Still Need to Do Manually

Due to AWS limitations, these must be created manually:

- AWS Bedrock Agent (no Terraform support yet)
- Bedrock Knowledge Bases (limited Terraform support)
- OpenSearch Serverless collections (for Knowledge Bases)
- EC2 instance for frontend (optional, or use CloudShell for testing)

## Prerequisites

### Required Tools

1. AWS CLI installed and configured
2. Terraform installed (version 1.0 or higher)
3. Git (to clone the repository)

### Quick Setup in AWS CloudShell (Recommended for Beginners)

CloudShell already has AWS CLI configured. You just need to install Terraform:

1. Open AWS CloudShell from the AWS Console
2. Install Terraform:

```bash
# Download Terraform
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip

# Unzip
unzip terraform_1.6.6_linux_amd64.zip

# Move to bin directory
mkdir -p ~/bin
mv terraform ~/bin/

# Add to PATH
echo 'export PATH=$PATH:~/bin' >> ~/.bashrc
source ~/.bashrc

# Verify installation
terraform version
```

### Required Information

Before starting, gather:

1. Zendesk credentials:
   - Domain (e.g., yourcompany.zendesk.com)
   - Email address
   - API token
2. Slack credentials:
   - Bot token (starts with xoxb-)
   - Team URL
3. AWS region where you want to deploy

## Step-by-Step Deployment

### Step 1: Clone or Upload the Repository

In CloudShell or your terminal:

```bash
# If using Git
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO/Zendesk_SME_Finder/terraform

# Or upload via CloudShell's Upload feature and then:
cd ~/Zendesk_SME_Finder/terraform
```

### Step 2: Create Your Variables File

Copy the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit the file with your actual values:

```bash
nano terraform.tfvars
```

Fill in your information:

```hcl
# AWS Configuration
aws_region  = "us-east-1"
environment = "production"

# Zendesk Credentials
zendesk_domain    = "yourcompany.zendesk.com"
zendesk_email     = "your-email@company.com"
zendesk_api_token = "your-actual-token-here"

# Slack Credentials
slack_bot_token = "xoxb-your-actual-token-here"
slack_team_url  = "https://your-workspace.slack.com/"

# Leave these empty for now
bedrock_agent_id       = ""
bedrock_agent_alias_id = ""
```

Save and exit (Ctrl+X, then Y, then Enter in nano).

### Step 3: Initialize Terraform

This downloads the necessary provider plugins:

```bash
terraform init
```

You should see "Terraform has been successfully initialized!"

### Step 4: Review the Deployment Plan

See what Terraform will create:

```bash
terraform plan
```

Review the output. It should show approximately 20+ resources to be created.

### Step 5: Deploy the Infrastructure

Apply the Terraform configuration:

```bash
terraform apply
```

- Type `yes` when prompted
- Wait 2-3 minutes for deployment to complete

You should see "Apply complete!" with a summary of created resources.

### Step 6: View Outputs

Get the API endpoint and key:

```bash
# View all outputs
terraform output

# Get API endpoint
terraform output api_gateway_endpoint

# Get API key (sensitive)
terraform output -raw api_key
```

Save these values - you'll need them for the frontend.

### Step 7: Create Bedrock Agent (Manual)

Now create the Bedrock Agent in the AWS Console:

1. Go to Amazon Bedrock Console
2. Click "Agents" in the left sidebar
3. Click "Create Agent"

**Basic Configuration:**
- Name: `zendesk-sme-finder-agent`
- Model: Claude Sonnet 4.5
- IAM role: Look for `zendesk-sme-finder-bedrock-agent-role` (created by Terraform)

**Instructions:** Copy from the manual deployment guide or use:

```
You are an intelligent FDE finder for Zendesk support tickets. Your goal is to analyze tickets and recommend the best FDEs to help resolve them.

WORKFLOW:
1. Fetch ticket details from Zendesk
2. Search similar-tickets knowledge base for historical matches
3. Search fde-profiles knowledge base for expert FDEs
4. Rank FDEs by expertise match
5. Create Slack conversation
6. Update Zendesk ticket

Return JSON with recommended_fdes, similar_tickets, slack_conversation_url, and zendesk_updated fields.
```

**Add Action Groups:**

Get Lambda ARNs from Terraform:

```bash
terraform output lambda_functions
```

1. Add Zendesk Action Group:
   - Lambda: Use the zendesk_actions ARN
   - Schema: See `AWS_DEPLOYMENT_GUIDE_BEGINNERS.md` for the OpenAPI schema

2. Add Slack Action Group:
   - Lambda: Use the slack_actions ARN
   - Schema: See `AWS_DEPLOYMENT_GUIDE_BEGINNERS.md` for the OpenAPI schema

**Add Knowledge Bases:**
(You need to create these manually first - see manual guide)

1. Select `similar-tickets-kb`
2. Select `fde-profiles-kb`

**Prepare and Create Alias:**

1. Click "Prepare"
2. Click "Create Alias"
3. Name: `production`
4. Copy the Agent ID and Alias ID

### Step 8: Update Terraform with Agent IDs

Edit your terraform.tfvars file:

```bash
nano terraform.tfvars
```

Add the Agent IDs:

```hcl
bedrock_agent_id       = "YOUR_AGENT_ID"
bedrock_agent_alias_id = "YOUR_ALIAS_ID"
```

Apply the update:

```bash
terraform apply
```

Type `yes` when prompted.

### Step 9: Configure the Frontend

Create the frontend environment file:

```bash
cd ../frontend

# Get values from Terraform
API_ENDPOINT=$(cd ../terraform && terraform output -raw api_gateway_endpoint)
API_KEY=$(cd ../terraform && terraform output -raw api_key)

# Create .env file
cat > .env << EOF
API_ENDPOINT=$API_ENDPOINT
API_KEY=$API_KEY
EOF

echo "Frontend configuration created!"
```

### Step 10: Test the Deployment

Test the API directly:

```bash
# Get your API endpoint and key
cd ../terraform
API_ENDPOINT=$(terraform output -raw api_gateway_endpoint)
API_KEY=$(terraform output -raw api_key)

# Test API call
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"ticket_id": "12345"}'
```

You should get a JSON response with FDE recommendations.

## Managing Your Infrastructure

### View Current State

```bash
# List all resources
terraform state list

# Show specific resource details
terraform show

# View outputs
terraform output
```

### Update Infrastructure

After changing any .tf files or variables:

```bash
terraform plan   # Preview changes
terraform apply  # Apply changes
```

### Destroy Infrastructure

To remove all resources (avoid ongoing charges):

```bash
terraform destroy
```

Type `yes` when prompted. This will delete:
- All Lambda functions
- API Gateway
- Secrets
- IAM roles
- CloudWatch logs

Note: This does NOT delete:
- Bedrock Agent (delete manually)
- Knowledge Bases (delete manually)
- OpenSearch collections (delete manually)

## Troubleshooting

### Error: "Error creating Lambda function"

**Cause:** Dependencies not installed or ZIP file too large.

**Solution:**
```bash
# Clean and rebuild
rm -rf builds/
terraform apply
```

### Error: "Access denied" when creating IAM role

**Cause:** Your AWS user doesn't have IAM permissions.

**Solution:** Ask your AWS administrator to grant you IAM permissions, or use an admin account.

### Error: "Secret already exists"

**Cause:** Secrets from a previous deployment exist.

**Solution:**
```bash
# Delete old secrets (they have a recovery window)
aws secretsmanager delete-secret --secret-id zendesk-sme-finder/zendesk-credentials --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id zendesk-sme-finder/slack-credentials --force-delete-without-recovery

# Then retry
terraform apply
```

### Lambda function doesn't have dependencies

**Cause:** The Lambda layer didn't build correctly.

**Solution:**
```bash
# Create builds directory
mkdir -p builds/python

# Install dependencies manually
pip3 install -r ../lambdas/action-groups/zendesk/requirements.txt -t builds/python/
pip3 install -r ../lambdas/action-groups/slack/requirements.txt -t builds/python/

# Reapply
terraform apply
```

### How to view CloudWatch logs

```bash
# Get log group names
terraform output cloudwatch_log_groups

# View logs in AWS Console or use CLI
aws logs tail /aws/lambda/zendesk-sme-finder-orchestration --follow
```

## Cost Estimation

Terraform-managed resources cost approximately:

| Resource | Monthly Cost |
|----------|--------------|
| Lambda (3 functions, 100 invocations/month) | $0.05 |
| API Gateway (100 requests/month) | $0.01 |
| Secrets Manager (2 secrets) | $0.80 |
| CloudWatch Logs (minimal data) | $0.50 |
| **Total** | **$1.36/month** |

Plus manually created resources:
- Bedrock usage: ~$0.70/month
- OpenSearch Serverless: ~$1.50/month
- EC2 (if used): ~$15/month

## Advanced Configuration

### Using Different Regions

Edit terraform.tfvars:

```hcl
aws_region = "us-west-2"
```

Then apply:

```bash
terraform apply
```

### Customizing Lambda Settings

Edit terraform.tfvars:

```hcl
lambda_timeout              = 90
lambda_memory_size          = 1024
orchestration_lambda_timeout = 180
```

### Adding Custom Tags

Edit terraform.tfvars:

```hcl
additional_tags = {
  Owner      = "Engineering Team"
  CostCenter = "CC-12345"
  Project    = "Customer Support"
}
```

### Multiple Environments

Create separate tfvars files:

```bash
# Development
cp terraform.tfvars terraform.dev.tfvars
# Edit for dev settings

# Production
cp terraform.tfvars terraform.prod.tfvars
# Edit for prod settings

# Deploy to dev
terraform apply -var-file=terraform.dev.tfvars

# Deploy to prod
terraform apply -var-file=terraform.prod.tfvars
```

## Terraform State Management

### Local State (Default)

Terraform stores state in `terraform.tfstate` locally. This is fine for individual use.

### Remote State (Recommended for Teams)

Use S3 backend for team collaboration:

Create `backend.tf`:

```hcl
terraform {
  backend "s3" {
    bucket = "your-terraform-state-bucket"
    key    = "zendesk-sme-finder/terraform.tfstate"
    region = "us-east-1"

    # Optional: Enable state locking
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
```

Initialize:

```bash
terraform init -migrate-state
```

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/terraform.yml`:

```yaml
name: Terraform Deploy

on:
  push:
    branches: [main]
    paths: [terraform/**]

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2

      - name: Terraform Init
        run: terraform init
        working-directory: terraform

      - name: Terraform Plan
        run: terraform plan
        working-directory: terraform
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve
        working-directory: terraform
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

## Next Steps

After successful Terraform deployment:

1. Create Knowledge Bases manually (see manual deployment guide)
2. Create OpenSearch Serverless collections
3. Create and configure Bedrock Agent
4. Update terraform.tfvars with Agent IDs and reapply
5. Deploy frontend to EC2 or test locally
6. Test end-to-end with real tickets
7. Set up monitoring and alerts
8. Configure automated backups

## Getting Help

If you encounter issues:

1. Check Terraform output for error messages
2. Review CloudWatch logs: `terraform output cloudwatch_log_groups`
3. Verify all credentials in terraform.tfvars are correct
4. Ensure you're using the same AWS region throughout
5. Check the manual deployment guide for additional context

## Comparison: Terraform vs Manual Deployment

| Task | Manual | Terraform |
|------|--------|-----------|
| Create IAM roles | 15 minutes | Automatic |
| Create Lambda functions | 30 minutes | Automatic |
| Package Lambda code | 20 minutes | Automatic |
| Create API Gateway | 20 minutes | Automatic |
| Create Secrets | 10 minutes | Automatic |
| Setup CORS | 10 minutes | Automatic |
| Create API key | 5 minutes | Automatic |
| Total time saved | 110 minutes | 5 minutes setup |

Terraform reduces deployment time by 95% and eliminates human error.

---

For additional support, refer to:
- AWS_DEPLOYMENT_GUIDE_BEGINNERS.md (manual deployment steps)
- README.md (project overview)
- Terraform documentation: https://terraform.io/docs
