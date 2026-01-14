# Step Functions Workflows

This directory contains AWS Step Functions state machine definitions for orchestrating the SME matching process.

## SME Matching Workflow

**File**: `sme-matching-workflow.json`

### Overview

The SME Matching Workflow coordinates the entire process from ticket arrival to Slack notification:

1. **Input Validation**: Verify ticket_id, S3 bucket, and key
2. **Embedding Check**: Determine if embedding already exists
3. **Embedding Generation**: Generate vector embedding if needed (optional)
4. **RAG Pipeline**: Run vector search and SME matching on ECS Fargate
5. **Validation**: Check confidence scores and SME availability
6. **Slack Notification**: Send recommendations to CRE
7. **Error Handling**: Handle failures and low confidence scenarios

### Workflow States

```
ValidateInput
  |
CheckEmbeddingExists
  | (if false)
  ├─> GenerateEmbedding --> WaitForEmbedding
  |
RunRAGPipeline (ECS Fargate)
  |
ParseRAGOutput
  |
ValidateSMERecommendations
  | (if confidence < 0.6)
  ├─> LowConfidenceAlert --> ManualEscalation
  | (if no SMEs found)
  ├─> NoSMEsFound --> ManualEscalation
  |
SendSlackNotification
  |
WorkflowSuccess
```

### Input Format

```json
{
  "ticket_id": "12345",
  "bucket": "zendesk-sme-tickets",
  "key": "raw-tickets/year=2025/month=01/day=05/ticket-12345.json",
  "embedding_exists": true,
  "timestamp": "2025-01-05T10:00:00Z"
}
```

### Output Format

```json
{
  "ticket_id": "12345",
  "sme_recommendations": {
    "top_smes": [
      {
        "cre_id": "cre001",
        "name": "John Doe",
        "confidence": 0.92,
        "reasoning": "Strong PostgreSQL expertise, resolved 15 similar issues",
        "slack_id": "U12345"
      },
      {
        "cre_id": "cre002",
        "name": "Jane Smith",
        "confidence": 0.88,
        "reasoning": "Database performance specialist, AWS RDS certified",
        "slack_id": "U67890"
      },
      {
        "cre_id": "cre003",
        "name": "Bob Johnson",
        "confidence": 0.85,
        "reasoning": "PostgreSQL expert, similar customer experience",
        "slack_id": "U11111"
      }
    ],
    "reasoning": "Based on semantic similarity and historical success rates",
    "confidence": 0.88
  },
  "slack_result": {
    "message_ts": "1704448800.123456",
    "channel": "C12345"
  }
}
```

### Error Handling

#### Retry Configuration

**ECS Task (RAG Pipeline)**:
- Max Attempts: 2
- Backoff Rate: 2.0
- Interval: 5 seconds
- Timeout: 300 seconds (5 minutes)

**Lambda Functions**:
- Max Attempts: 2
- Backoff Rate: 2.0
- Interval: 3 seconds

#### Failure States

1. **ValidationFailed**: Input validation failed
   - Check ticket_id, bucket, key parameters
   - Verify S3 object exists

2. **EmbeddingGenerationFailed**: Embedding generation failed
   - Check Bedrock connectivity
   - Verify Pinecone API key
   - Check Lambda logs

3. **RAGPipelineFailed**: RAG engine failed
   - Check ECS task logs
   - Verify Pinecone index exists
   - Check network connectivity

4. **SlackNotificationFailed**: Slack notification failed
   - Verify Slack bot token
   - Check CRE Slack ID mapping
   - Review Slack API errors

### Low Confidence Handling

If the top SME has confidence < 0.6:
- Workflow triggers `LowConfidenceAlert`
- Sends alert to operations team
- Transitions to `ManualEscalation` state
- Operations team manually reviews and assigns SME

### Deployment

#### Prerequisites

1. Replace placeholders in the JSON file:
   - `${AWS_REGION}`
   - `${AWS_ACCOUNT_ID}`
   - `${PRIVATE_SUBNET_1}`
   - `${PRIVATE_SUBNET_2}`
   - `${ECS_SECURITY_GROUP}`

2. Ensure all Lambda functions and ECS task definitions exist

#### Using AWS CLI

```bash
# Substitute environment variables
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=123456789012
export PRIVATE_SUBNET_1=subnet-abc123
export PRIVATE_SUBNET_2=subnet-def456
export ECS_SECURITY_GROUP=sg-xyz789

# Use envsubst to replace placeholders
cat sme-matching-workflow.json | envsubst > sme-matching-workflow-final.json

# Create state machine
aws stepfunctions create-state-machine \
  --name sme-matching-workflow \
  --definition file://sme-matching-workflow-final.json \
  --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/StepFunctionsExecutionRole \
  --type STANDARD \
  --logging-configuration level=ALL,includeExecutionData=true,destinations=[{cloudWatchLogsLogGroup={logGroupArn=arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/vendedlogs/states/sme-matching-workflow}}]
```

#### Using Terraform

See `infrastructure/modules/step-functions/` for Terraform configuration.

### Testing

#### Manual Execution

```bash
# Start execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:sme-matching-workflow \
  --name test-execution-$(date +%s) \
  --input '{
    "ticket_id": "12345",
    "bucket": "zendesk-sme-tickets",
    "key": "raw-tickets/year=2025/month=01/day=05/ticket-12345.json",
    "embedding_exists": true
  }'

# Get execution status
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn <execution-arn>
```

#### Viewing Execution Graph

1. Open AWS Step Functions Console
2. Navigate to State Machines
3. Click on `sme-matching-workflow`
4. Click on an execution to view visual graph

### Monitoring

#### CloudWatch Metrics

Step Functions automatically publishes:
- `ExecutionsStarted`
- `ExecutionsSucceeded`
- `ExecutionsFailed`
- `ExecutionTime`

#### Custom Metrics

Each Lambda function publishes additional metrics:
- RAG pipeline duration
- Confidence scores
- Slack notification success rate

#### CloudWatch Logs

All executions are logged to:
`/aws/vendedlogs/states/sme-matching-workflow`

Log format:
```json
{
  "execution_arn": "...",
  "input": {...},
  "output": {...},
  "status": "SUCCEEDED",
  "start_date": "...",
  "stop_date": "..."
}
```

### Cost Optimization

**Standard Workflow Pricing**:
- $0.025 per 1,000 state transitions
- Average workflow: 8-10 state transitions
- 1000 executions/month: ~$0.20/month

**Best Practices**:
1. Use `STANDARD` type (not EXPRESS) for better debugging
2. Enable execution logging for troubleshooting
3. Set appropriate timeouts to prevent runaway costs
4. Monitor failed executions and optimize retry logic

### Troubleshooting

#### Common Issues

**Issue**: Execution fails at `RunRAGPipeline`
- **Cause**: ECS task timeout or failure
- **Solution**: Check ECS task logs, increase timeout, verify network configuration

**Issue**: Low confidence alerts too frequent
- **Cause**: Poor vector similarity or insufficient historical data
- **Solution**: Lower threshold, improve CRE profile data, retrain embeddings

**Issue**: Workflow stuck in `WaitForEmbedding`
- **Cause**: Embedding generation failed silently
- **Solution**: Check embedding-generator Lambda logs, verify Pinecone connectivity

### IAM Role

The Step Functions execution role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:*:*:function:validate-input",
        "arn:aws:lambda:*:*:function:embedding-generator",
        "arn:aws:lambda:*:*:function:slack-bot",
        "arn:aws:lambda:*:*:function:low-confidence-handler"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask",
        "ecs:DescribeTasks",
        "ecs:StopTask"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries",
        "logs:PutResourcePolicy",
        "logs:DescribeResourcePolicies",
        "logs:DescribeLogGroups"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/ECSTaskExecutionRole"
    }
  ]
}
```

## References

- [AWS Step Functions Documentation](https://docs.aws.amazon.com/step-functions/)
- [State Machine Definition](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-amazon-states-language.html)
- [ECS Integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html)
