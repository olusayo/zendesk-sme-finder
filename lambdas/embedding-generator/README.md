# Embedding Generator Lambda

This Lambda function generates vector embeddings for Zendesk tickets using AWS Bedrock Titan Embeddings and stores them in Pinecone for semantic search.

## Overview

**Trigger**: S3 event notification when a new ticket is uploaded to the raw-tickets folder

**Process Flow**:
1. Read ticket data from S3
2. Prepare comprehensive embedding text (subject + description + tags + conversation history)
3. Generate 1024-dimensional embedding using Bedrock Titan
4. Store vector in Pinecone with metadata
5. Trigger Step Functions workflow for SME matching

## Configuration

### Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<your-account-id>

# S3 Buckets
S3_BUCKET_TICKETS=zendesk-sme-tickets

# Bedrock Model
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# Pinecone
PINECONE_API_KEY=<your-pinecone-key>
PINECONE_INDEX_NAME=zendesk-sme-finder

# Step Functions
STEP_FUNCTION_ARN=arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:sme-matching-workflow
```

### Lambda Configuration

- **Runtime**: Python 3.12
- **Memory**: 1024 MB
- **Timeout**: 60 seconds
- **Concurrency**: 50

### IAM Permissions

The Lambda execution role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::zendesk-sme-tickets/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"
    },
    {
      "Effect": "Allow",
      "Action": [
        "states:StartExecution"
      ],
      "Resource": "arn:aws:states:*:*:stateMachine:sme-matching-workflow"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

## Embedding Strategy

### Text Preparation

The function combines multiple ticket fields for rich semantic representation:

```python
embedding_text = f"""
Ticket ID: {ticket_id}
Customer: {customer}
Priority: {priority}
Subject: {subject}
Description: {description}
Tags: {tags}
Recent Conversation: {last_5_messages}
"""
```

### Pinecone Metadata

Each vector is stored with the following metadata:

```json
{
  "ticket_id": "12345",
  "customer_id": "CUST001",
  "customer_name": "Acme Corp",
  "priority": "high",
  "created_at": "2025-01-05T10:00:00Z",
  "tags": ["database", "performance", "postgresql"],
  "subject": "PostgreSQL performance degradation",
  "cre_id": "cre001",
  "resolution_success": false,
  "timestamp": "2025-01-05T10:05:00Z"
}
```

## Metrics

The function publishes the following CloudWatch metrics:

- `BedrockTokensUsed`: Number of input tokens processed
- `BedrockThrottling`: Count of throttling events
- `PineconeUpsertSuccess`: Successful vector storage operations
- `PineconeUpsertFailure`: Failed vector storage operations
- `StepFunctionTriggered`: Step Functions workflow starts
- `ProcessingDuration`: End-to-end processing time (milliseconds)
- `Success`: Successful completions
- `Failure`: Failed executions

## Error Handling

### Bedrock Throttling

The function handles Bedrock throttling with automatic retries:
- Exponential backoff (boto3 default)
- Max 3 retry attempts
- Logs throttling events for monitoring

### Pinecone Failures

If Pinecone storage fails:
- Error is logged with full context
- Metric is published
- Exception is raised to trigger Lambda retry

### S3 Read Errors

If S3 read fails:
- Error is logged
- Exception is raised
- DLQ receives failed event for manual investigation

## Testing

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AWS_REGION=us-east-1
export PINECONE_API_KEY=your-key
# ... other env vars

# Run with sample event
python -c "
import json
from handler import lambda_handler

event = {
    'Records': [{
        's3': {
            'bucket': {'name': 'zendesk-sme-tickets'},
            'object': {'key': 'raw-tickets/year=2025/month=01/day=05/ticket-12345.json'}
        }
    }]
}

class Context:
    request_id = 'test-request-id'

result = lambda_handler(event, Context())
print(json.dumps(result, indent=2))
"
```

### Integration Testing

```bash
# Upload test ticket to S3 (triggers Lambda)
aws s3 cp test-ticket.json s3://zendesk-sme-tickets/raw-tickets/year=2025/month=01/day=05/

# Check Lambda logs
aws logs tail /aws/lambda/embedding-generator --follow

# Verify Pinecone storage
# (Use Pinecone console or SDK to query)
```

## Deployment

### Using AWS CLI

```bash
# Package dependencies
cd lambdas/embedding-generator
pip install -r requirements.txt -t package/
cp handler.py package/

# Create deployment package
cd package
zip -r ../deployment.zip .
cd ..

# Deploy
aws lambda update-function-code \
  --function-name embedding-generator \
  --zip-file fileb://deployment.zip
```

### Using Terraform

See `infrastructure/modules/lambda/embedding-generator/` for Terraform configuration.

## Monitoring

### CloudWatch Dashboards

Monitor these key metrics:
- Embedding generation rate (requests/minute)
- Bedrock token usage (cost tracking)
- Pinecone upsert success rate
- Processing latency (p50, p99)
- Error rate

### Alerts

Recommended alarms:
- High error rate (>5%)
- High latency (>30 seconds)
- Bedrock throttling (>10 events/hour)
- Pinecone failures (>2%)

## Cost Optimization

### Bedrock Costs

- Titan Embeddings: $0.0001 per 1K tokens
- Average ticket: ~500 tokens = $0.00005 per ticket
- 1000 tickets/month = ~$0.50/month

### Optimization Strategies

1. **Text Truncation**: Limit conversation history to last 5 messages
2. **Caching**: Store embeddings in S3 as backup (avoid regeneration)
3. **Batch Processing**: Process multiple tickets in parallel

## Troubleshooting

### Common Issues

**Issue**: Lambda timeout
- **Cause**: Slow Bedrock/Pinecone response
- **Solution**: Increase timeout to 90 seconds

**Issue**: Pinecone connection errors
- **Cause**: Invalid API key or network issues
- **Solution**: Verify API key in Secrets Manager, check VPC configuration

**Issue**: Step Function not triggered
- **Cause**: Missing IAM permissions
- **Solution**: Add `states:StartExecution` permission

## References

- [AWS Bedrock Titan Embeddings](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [Pinecone Python SDK](https://docs.pinecone.io/docs/python-client)
- [AWS Step Functions](https://docs.aws.amazon.com/step-functions/)
