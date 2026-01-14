# Data Preparation Guide
## Zendesk SME Finder - Knowledge Base Data Sources

This guide explains how to prepare and upload data to the Bedrock Knowledge Bases.

---

## Overview

The Zendesk SME Finder uses two Knowledge Bases:
1. **Similar Tickets KB** - Historical Zendesk tickets with resolutions
2. **FDE Profiles KB** - Field Development Engineer expertise and certifications

**Data Source**: Originally stored in Google Cloud Platform (GCP) BigQuery
**Format**: Exported as CSV files for AWS Bedrock Knowledge Bases
**Storage**: AWS S3 buckets (auto-created by Terraform)

---

## Data Source Architecture

### Original Data Location: GCP BigQuery

The project data originates from BigQuery tables:
- Zendesk ticket data (subject, description, tags, resolutions, assigned engineers)
- FDE certification and expertise data (names, emails, skills, past successes)

### Why CSV Export Instead of Direct Integration?

**Decision**: Export CSV files from BigQuery rather than BigQuery MCP integration

**Reasoning**:
1. **Simplicity**: Bedrock Knowledge Bases natively support S3 data sources
2. **Performance**: Direct S3 access is faster than cross-cloud queries
3. **Cost**: Avoids continuous BigQuery API calls and cross-cloud data transfer fees
4. **Snapshot Approach**: KB data doesn't need real-time updates (periodic refresh is sufficient)
5. **AWS-Native**: Keeps the AWS deployment self-contained

**Trade-off**: Requires periodic data exports to keep Knowledge Bases current

---

## Data Export Process

### Step 1: Export from BigQuery

If you need to refresh data from BigQuery:

```sql
-- Export Tickets
EXPORT DATA OPTIONS(
  uri='gs://your-gcs-bucket/tickets/*.csv',
  format='CSV',
  overwrite=true,
  header=true
) AS
SELECT
  ticket_id,
  subject,
  description,
  tags,
  status,
  priority,
  assigned_engineer,
  resolution_notes,
  created_at,
  resolved_at
FROM `your-project.zendesk.tickets`
WHERE status = 'solved'
  AND resolved_at IS NOT NULL
LIMIT 10000;

-- Export FDE Profiles
EXPORT DATA OPTIONS(
  uri='gs://your-gcs-bucket/fde-profiles/*.csv',
  format='CSV',
  overwrite=true,
  header=true
) AS
SELECT
  fde_name,
  email,
  certifications,
  expertise_areas,
  years_experience,
  successful_tickets,
  specializations,
  region
FROM `your-project.fde_data.profiles`
WHERE status = 'active';
```

### Step 2: Download from GCS to Local

```bash
# Install Google Cloud SDK if needed
# Download tickets
gsutil -m cp -r gs://your-gcs-bucket/tickets/*.csv ./data/

# Download FDE profiles
gsutil -m cp -r gs://your-gcs-bucket/fde-profiles/*.csv ./data/
```

---

## Data Format Requirements

### Tickets CSV Format

Required columns:
- `ticket_id` - Unique ticket identifier
- `subject` - Ticket subject line
- `description` - Full ticket description
- `tags` - Comma-separated tags
- `resolution_notes` - How the ticket was resolved
- `assigned_engineer` - Engineer who solved it

Optional columns:
- `priority`, `status`, `created_at`, `resolved_at`

Example:
```csv
ticket_id,subject,description,tags,assigned_engineer,resolution_notes
12345,"Database slow","PostgreSQL queries taking 30+ seconds","database,performance,postgresql","john@example.com","Added index on user_id column, query time reduced to <1s"
12346,"API timeout","Customer API calls timing out after 10s","api,timeout,python","jane@example.com","Increased connection pool size from 10 to 50"
```

### FDE Profiles CSV Format

Required columns:
- `fde_name` - Full name
- `email` - Contact email
- `expertise_areas` - Comma-separated areas
- `certifications` - Relevant certifications

Optional columns:
- `years_experience`, `successful_tickets`, `specializations`, `region`

Example:
```csv
fde_name,email,expertise_areas,certifications,specializations
"John Doe","john.doe@example.com","PostgreSQL,MySQL,Database Performance","AWS Solutions Architect,PostgreSQL DBA","Query optimization, Index tuning"
"Jane Smith","jane.smith@example.com","Python,API Development,FastAPI","AWS Developer Associate,Python PCAP","REST APIs, Async programming"
```

---

## S3 Upload Instructions

### Automated: Terraform Creates Buckets

When you run Terraform, it automatically creates:
- S3 bucket: `zendesk-sme-finder-kb-data-{account-id}`
- Folders: `tickets/` and `fde-profiles/`

**After Terraform deployment**, upload your CSV files:

### Option 1: AWS CLI Upload (Recommended)

```bash
# Get bucket name from Terraform output
BUCKET_NAME=$(cd terraform && terraform output -raw s3_data_bucket.bucket_name)

# Upload tickets data
aws s3 cp ./data/tickets/ s3://${BUCKET_NAME}/tickets/ --recursive \
  --exclude "*" --include "*.csv"

# Upload FDE profiles data
aws s3 cp ./data/fde-profiles/ s3://${BUCKET_NAME}/fde-profiles/ --recursive \
  --exclude "*" --include "*.csv"

# Verify uploads
aws s3 ls s3://${BUCKET_NAME}/tickets/
aws s3 ls s3://${BUCKET_NAME}/fde-profiles/
```

### Option 2: AWS Console Upload

1. Go to AWS S3 Console: https://s3.console.aws.amazon.com/
2. Find bucket: `zendesk-sme-finder-kb-data-{account-id}`
3. Navigate to `tickets/` folder
4. Click "Upload" → "Add files"
5. Select your ticket CSV files
6. Click "Upload"
7. Repeat for `fde-profiles/` folder

### Option 3: Terraform Upload (Automated)

Add this to `terraform/s3_data.tf`:

```hcl
# Upload tickets data
resource "aws_s3_object" "tickets_data" {
  for_each = fileset("${path.module}/../data/tickets/", "*.csv")

  bucket = aws_s3_bucket.knowledge_base_data.id
  key    = "tickets/${each.value}"
  source = "${path.module}/../data/tickets/${each.value}"
  etag   = filemd5("${path.module}/../data/tickets/${each.value}")
}

# Upload FDE profiles data
resource "aws_s3_object" "fde_profiles_data" {
  for_each = fileset("${path.module}/../data/fde-profiles/", "*.csv")

  bucket = aws_s3_bucket.knowledge_base_data.id
  key    = "fde-profiles/${each.value}"
  source = "${path.module}/../data/fde-profiles/${each.value}"
  etag   = filemd5("${path.module}/../data/fde-profiles/${each.value}")
}
```

Then place your CSV files in:
- `data/tickets/*.csv`
- `data/fde-profiles/*.csv`

And run: `terraform apply`

---

## Trigger Knowledge Base Ingestion

After uploading data to S3, trigger ingestion to populate the Knowledge Bases:

### Get Knowledge Base IDs

```bash
cd terraform

# Get tickets KB ID
TICKETS_KB_ID=$(terraform output -raw bedrock_resources.tickets_kb_id)
TICKETS_DS_ID=$(terraform output -raw bedrock_resources.tickets_data_source)

# Get FDE profiles KB ID
FDE_KB_ID=$(terraform output -raw bedrock_resources.fde_profiles_kb_id)
FDE_DS_ID=$(terraform output -raw bedrock_resources.fde_profiles_data_source)
```

### Start Ingestion Jobs

```bash
# Ingest tickets data
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $TICKETS_KB_ID \
  --data-source-id $TICKETS_DS_ID

# Ingest FDE profiles data
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $FDE_KB_ID \
  --data-source-id $FDE_DS_ID
```

### Monitor Ingestion Progress

```bash
# Check tickets ingestion status
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $TICKETS_KB_ID \
  --data-source-id $TICKETS_DS_ID \
  --max-results 1

# Check FDE profiles ingestion status
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $FDE_KB_ID \
  --data-source-id $FDE_DS_ID \
  --max-results 1
```

Ingestion typically takes 2-10 minutes depending on data size.

---

## Sample Data Provided

The repository includes sample data for testing:

**Location**: `data/knowledge-bases/`
- `similar-tickets/sample-tickets.json` - Example ticket data
- `fde-profiles/sample-fdes.json` - Example FDE profiles

**Note**: These are JSON samples for reference. You need to export actual CSV data from BigQuery.

---

## Data Refresh Strategy

### When to Refresh Data

Refresh Knowledge Base data when:
1. New tickets are resolved (weekly/monthly)
2. FDE certifications or skills change (quarterly)
3. New FDEs join the team
4. Significant ticket volume increases

### Refresh Process

```bash
# 1. Export fresh data from BigQuery (see Step 1 above)
# 2. Upload to S3
aws s3 sync ./data/tickets/ s3://${BUCKET_NAME}/tickets/
aws s3 sync ./data/fde-profiles/ s3://${BUCKET_NAME}/fde-profiles/

# 3. Trigger re-ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $TICKETS_KB_ID \
  --data-source-id $TICKETS_DS_ID

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $FDE_KB_ID \
  --data-source-id $FDE_DS_ID
```

### Automated Refresh (Optional)

Create a Lambda function triggered by EventBridge (CloudWatch Events) to:
1. Export from BigQuery weekly
2. Upload to S3
3. Trigger ingestion automatically

---

## Data Size Recommendations

### Minimum Data for Testing
- Tickets: 100-500 resolved tickets
- FDE Profiles: 10-50 FDEs

### Production Data
- Tickets: 10,000+ resolved tickets (last 12-24 months)
- FDE Profiles: All active FDEs

### Performance Considerations
- Bedrock Knowledge Bases handle up to 1M documents per KB
- Larger datasets provide better similarity matching
- Balance data freshness vs. size

---

## Cost Considerations

### Storage Costs
- S3 storage: ~$0.023/GB/month
- 10,000 tickets (~100MB CSV): ~$0.002/month
- Minimal cost impact

### Knowledge Base Costs
- Ingestion: One-time per refresh
- Vector storage: Based on OpenSearch Serverless
- Query costs: Per search request

### Data Transfer
- BigQuery → GCS export: Free (same region)
- GCS → Local → S3: Data egress charges apply
- Recommendation: Export < 1GB at a time to minimize costs

---

## Troubleshooting

### Issue: Ingestion Failed

**Check**:
1. CSV files are valid (no malformed rows)
2. S3 bucket permissions allow Bedrock access
3. Data source IAM role has s3:GetObject permission

**Fix**:
```bash
# Verify file format
aws s3 cp s3://${BUCKET_NAME}/tickets/tickets.csv - | head -10

# Check IAM role permissions
aws iam get-role --role-name zendesk-sme-finder-kb-tickets-role
```

### Issue: No Results from Knowledge Base

**Check**:
1. Ingestion completed successfully
2. CSV files have content
3. Queries use relevant keywords

**Fix**:
- Re-trigger ingestion
- Verify CSV data quality
- Test with known ticket descriptions

### Issue: Poor Match Quality

**Improvement**:
1. Include more historical tickets
2. Add more detail to ticket descriptions
3. Ensure resolution notes are comprehensive
4. Update FDE profiles with detailed expertise

---

## Alternative: BigQuery MCP Integration (Future)

For real-time data access without CSV exports:

**Pros**:
- Always current data
- No export/upload process
- Single source of truth

**Cons**:
- Cross-cloud latency
- BigQuery API costs
- More complex architecture
- Requires MCP server setup

**Implementation** (if desired in future):
1. Set up BigQuery MCP server
2. Create Lambda function to query BigQuery
3. Cache results in Redis/DynamoDB
4. Update Bedrock Agent to use MCP tool

**Current Decision**: CSV export approach is simpler and more cost-effective for this use case.

---

## Summary

**Data Flow**:
```
BigQuery (GCP)
    ↓ (SQL Export)
Google Cloud Storage
    ↓ (gsutil download)
Local CSV files
    ↓ (aws s3 cp)
S3 Bucket (Auto-created by Terraform)
    ↓ (aws bedrock-agent start-ingestion-job)
Bedrock Knowledge Bases
    ↓ (Automatic vectorization)
OpenSearch Serverless
    ↓ (Query at runtime)
Bedrock Agent → FDE Recommendations
```

**Key Points**:
1. Data originates from BigQuery
2. CSV export chosen for simplicity and cost
3. Terraform creates S3 buckets automatically
4. You upload CSV files after Terraform deployment
5. Trigger ingestion to populate Knowledge Bases
6. Refresh periodically (weekly/monthly)

**Required Actions**:
1. Export CSV data from BigQuery
2. Run Terraform to create infrastructure
3. Upload CSV files to S3
4. Trigger Knowledge Base ingestion
5. Test the system with sample queries

---

**Questions?** See COMPLETE_DEPLOYMENT_GUIDE.md for full deployment instructions.
