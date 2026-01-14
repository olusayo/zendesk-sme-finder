# Ticket Ingestion Lambda

Handles Zendesk webhook events when CREs flag tickets with "need_sme" tag.

## Functionality

1. **Webhook Validation**: Verify HMAC signature from Zendesk
2. **Ticket Fetching**: Pull full ticket context via Zendesk API
3. **Data Validation**: Ensure ticket data is complete and valid
4. **S3 Storage**: Store raw ticket in S3 with date partitioning
5. **Trigger Downstream**: Invoke embedding generation Lambda

## Event Source

**API Gateway** with Zendesk webhook integration

## Trigger Example

```json
{
  "body": "{\"ticket_id\": 12345, \"tag_added\": \"need_sme\"}",
  "headers": {
    "X-Zendesk-Webhook-Signature": "abc123...",
    "X-Zendesk-Webhook-Signature-Timestamp": "1609459200"
  }
}
```

## Environment Variables

```bash
ZENDESK_DOMAIN=yourcompany.zendesk.com
ZENDESK_API_TOKEN=<from-secrets-manager>
ZENDESK_EMAIL=api@yourcompany.com
ZENDESK_WEBHOOK_SECRET=<webhook-secret>
S3_BUCKET_TICKETS=zendesk-sme-tickets
```

## Output

**S3 Object**:
- Bucket: `zendesk-sme-tickets`
- Key: `raw-tickets/year=2025/month=01/day=05/ticket-12345.json`
- Content: Full ticket context with comments

**Lambda Invocation**:
- Function: `embedding-generator`
- Payload: `{"ticket_id": "12345", "s3_bucket": "...", "s3_key": "..."}`

## Error Handling

- **Invalid Signature**: Return 401
- **Missing Ticket ID**: Return 400
- **Zendesk API Failure**: Retry 3x with exponential backoff
- **S3 Upload Failure**: Log error and return 500

## Metrics

- `SMEFinder/Pipeline/TicketIngested` (Count)
- `SMEFinder/Pipeline/EndToEndLatency` (Milliseconds)
- `SMEFinder/Pipeline/ErrorRate` (Percent)

## Testing

```bash
# Local testing
python -c "from handler import lambda_handler; lambda_handler(test_event, test_context)"

# Deploy and test
aws lambda invoke \
  --function-name ticket-ingestion \
  --payload file://test_event.json \
  output.json
```

## Deployment

```bash
# Create deployment package
zip -r function.zip handler.py zendesk_client.py validator.py

# Update Lambda function
aws lambda update-function-code \
  --function-name ticket-ingestion \
  --zip-file fileb://function.zip
```

## Dependencies

See [requirements.txt](./requirements.txt)

## IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arns3:::zendesk-sme-tickets/*"
    },
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": "arnlambda:*:*embedding-generator"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arnsecretsmanager:*:*zendesk/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arnlogs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": ["cloudwatch:PutMetricData"],
      "Resource": "*"
    }
  ]
}
```
