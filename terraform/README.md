# Terraform Infrastructure for Zendesk SME Finder

This directory contains Terraform configurations to automate the deployment of the Zendesk SME Finder infrastructure on AWS.

## Quick Start

```bash
# 1. Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Add your credentials

# 2. Initialize Terraform
terraform init

# 3. Preview changes
terraform plan

# 4. Deploy
terraform apply

# 5. View outputs
terraform output
```

## What Gets Deployed

This Terraform configuration creates:

- **IAM Roles & Policies**: Lambda execution role and Bedrock Agent role
- **Secrets Manager**: Zendesk and Slack credentials
- **Lambda Functions**: 3 functions (Zendesk actions, Slack actions, Orchestration)
- **API Gateway**: REST API with authentication
- **CloudWatch Log Groups**: For monitoring

## File Structure

```
terraform/
├── main.tf                        # Provider and main configuration
├── variables.tf                   # Input variables
├── outputs.tf                     # Output values
├── iam.tf                         # IAM roles and policies
├── secrets.tf                     # Secrets Manager resources
├── lambda.tf                      # Lambda functions
├── api_gateway.tf                 # API Gateway configuration
├── terraform.tfvars.example       # Example variables file
├── .gitignore                     # Git ignore rules
├── README.md                      # This file
└── TERRAFORM_DEPLOYMENT_GUIDE.md  # Detailed deployment guide

builds/                            # Generated during deployment
├── zendesk-actions.zip
├── slack-actions.zip
├── orchestration.zip
└── lambda-layer.zip
```

## Prerequisites

- AWS CLI configured with credentials
- Terraform 1.0 or higher
- Zendesk API credentials
- Slack bot token

## Configuration

### Required Variables

Edit `terraform.tfvars` with your values:

```hcl
# AWS Settings
aws_region  = "us-east-1"
environment = "production"

# Credentials
zendesk_domain    = "yourcompany.zendesk.com"
zendesk_email     = "api@yourcompany.com"
zendesk_api_token = "your-token"
slack_bot_token   = "xoxb-your-token"
slack_team_url    = "https://yourworkspace.slack.com/"

# Bedrock Agent (fill after manual creation)
bedrock_agent_id       = ""
bedrock_agent_alias_id = ""
```

### Optional Variables

Customize Lambda settings, API throttling, tags, etc. See [variables.tf](variables.tf) for all options.

## Deployment Steps

### 1. Initial Deployment

```bash
terraform init
terraform apply
```

### 2. Create Bedrock Agent Manually

The Bedrock Agent must be created manually in the AWS Console (Terraform doesn't support it yet).

Get the IAM role ARN for the agent:

```bash
terraform output bedrock_agent_role_arn
```

After creating the agent, get the Agent ID and Alias ID.

### 3. Update with Agent IDs

Edit `terraform.tfvars`:

```hcl
bedrock_agent_id       = "YOUR_AGENT_ID"
bedrock_agent_alias_id = "YOUR_ALIAS_ID"
```

Apply the update:

```bash
terraform apply
```

## Using Outputs

### Get API Endpoint

```bash
terraform output api_gateway_endpoint
```

### Get API Key (Sensitive)

```bash
terraform output -raw api_key
```

### Get All Frontend Config

```bash
terraform output -json frontend_config
```

### Export for Frontend

```bash
# Create .env file for Streamlit frontend
cat > ../frontend/.env << EOF
API_ENDPOINT=$(terraform output -raw api_gateway_endpoint)
API_KEY=$(terraform output -raw api_key)
EOF
```

## Testing

### Test API Endpoint

```bash
API_ENDPOINT=$(terraform output -raw api_gateway_endpoint)
API_KEY=$(terraform output -raw api_key)

curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"ticket_id": "12345"}'
```

### View Lambda Logs

```bash
# Get log group names
terraform output cloudwatch_log_groups

# Tail logs
aws logs tail /aws/lambda/zendesk-sme-finder-orchestration --follow
```

## Updating Infrastructure

### Update Lambda Code

After changing Lambda code:

```bash
terraform apply
```

Terraform will detect changes and redeploy the functions.

### Update Variables

After changing `terraform.tfvars`:

```bash
terraform apply
```

### Update Terraform Files

After editing `.tf` files:

```bash
terraform plan   # Preview changes
terraform apply  # Apply changes
```

## Cleanup

### Destroy All Resources

```bash
terraform destroy
```

Note: This does NOT delete manually created resources (Bedrock Agent, Knowledge Bases, OpenSearch collections).

### Partial Cleanup

Remove specific resources:

```bash
# Remove a specific Lambda
terraform destroy -target=aws_lambda_function.zendesk_actions

# Remove API Gateway
terraform destroy -target=aws_api_gateway_rest_api.main
```

## State Management

### Local State (Default)

State is stored in `terraform.tfstate` file locally.

**Important:** Don't commit this file to Git (already in .gitignore).

### Remote State (Recommended for Teams)

Use S3 backend for collaboration. Create `backend.tf`:

```hcl
terraform {
  backend "s3" {
    bucket = "your-terraform-state-bucket"
    key    = "zendesk-sme-finder/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
  }
}
```

Migrate:

```bash
terraform init -migrate-state
```

## Cost Estimation

Use AWS Cost Calculator or run:

```bash
terraform plan -out=tfplan
terraform show -json tfplan | terraform-cost-estimation
```

Estimated monthly cost with Terraform resources: ~$1.50/month

## Troubleshooting

### Issue: Dependencies not installing

```bash
# Clean and rebuild
rm -rf builds/
terraform apply
```

### Issue: API returns 403 Forbidden

Check API key:

```bash
terraform output -raw api_key
```

Verify it matches what you're using in requests.

### Issue: Lambda timeout

Increase timeout in `terraform.tfvars`:

```hcl
orchestration_lambda_timeout = 180
```

### Issue: Secrets already exist

Delete old secrets:

```bash
aws secretsmanager delete-secret \
  --secret-id zendesk-sme-finder/zendesk-credentials \
  --force-delete-without-recovery
```

## Best Practices

1. **Never commit terraform.tfvars** - Contains sensitive credentials
2. **Use remote state** - For team collaboration
3. **Review plans** - Always run `terraform plan` before `apply`
4. **Tag resources** - Use `additional_tags` for cost tracking
5. **Use workspaces** - For multiple environments

## Multiple Environments

### Using Workspaces

```bash
# Create dev workspace
terraform workspace new dev
terraform apply -var-file=terraform.dev.tfvars

# Switch to prod
terraform workspace select prod
terraform apply -var-file=terraform.prod.tfvars

# List workspaces
terraform workspace list
```

### Using Separate Directories

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf -> ../../main.tf
│   │   └── terraform.tfvars
│   └── prod/
│       ├── main.tf -> ../../main.tf
│       └── terraform.tfvars
```

## CI/CD Integration

See `TERRAFORM_DEPLOYMENT_GUIDE.md` for GitHub Actions and other CI/CD examples.

## Documentation

- **TERRAFORM_DEPLOYMENT_GUIDE.md** - Detailed step-by-step deployment instructions
- **AWS_DEPLOYMENT_GUIDE_BEGINNERS.md** - Manual deployment for comparison
- **variables.tf** - All configurable variables
- **outputs.tf** - All output values

## Support

For issues or questions:

1. Check `TERRAFORM_DEPLOYMENT_GUIDE.md` for detailed troubleshooting
2. Review Terraform plan output for errors
3. Check CloudWatch logs for Lambda errors
4. Verify all credentials are correct in `terraform.tfvars`

## Version Requirements

- Terraform: >= 1.0
- AWS Provider: ~> 5.0
- Archive Provider: ~> 2.4

## License

See project root LICENSE file.
