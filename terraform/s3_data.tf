# S3 Buckets for Knowledge Base Data Sources
# These buckets store the historical ticket data and FDE profiles

# S3 Bucket for Knowledge Base data
resource "aws_s3_bucket" "knowledge_base_data" {
  bucket = "${var.project_name}-kb-data-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.project_name}-knowledge-base-data"
    Description = "Storage for Knowledge Base data sources (tickets and FDE profiles)"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "knowledge_base_data" {
  bucket = aws_s3_bucket.knowledge_base_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "knowledge_base_data" {
  bucket = aws_s3_bucket.knowledge_base_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "knowledge_base_data" {
  bucket = aws_s3_bucket.knowledge_base_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy to manage old versions
resource "aws_s3_bucket_lifecycle_configuration" "knowledge_base_data" {
  bucket = aws_s3_bucket.knowledge_base_data.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# Create folder structure for different data sources
resource "aws_s3_object" "tickets_folder" {
  bucket       = aws_s3_bucket.knowledge_base_data.id
  key          = "tickets/"
  content_type = "application/x-directory"
}

resource "aws_s3_object" "fde_profiles_folder" {
  bucket       = aws_s3_bucket.knowledge_base_data.id
  key          = "fde-profiles/"
  content_type = "application/x-directory"
}

# Upload sample/placeholder data files if provided
# Users can replace these with real data later
resource "aws_s3_object" "tickets_readme" {
  bucket       = aws_s3_bucket.knowledge_base_data.id
  key          = "tickets/README.txt"
  content      = <<-EOF
    # Historical Tickets Data

    Upload your historical Zendesk ticket CSV files to this folder.

    Expected format:
    - ticket_id: Unique ticket identifier
    - subject: Ticket subject/title
    - description: Detailed ticket description
    - resolution: How the ticket was resolved
    - tags: Comma-separated tags/categories
    - assigned_fde: FDE who resolved the ticket
    - resolution_time_hours: Time taken to resolve

    After uploading new files, trigger Knowledge Base sync/ingestion via:
    aws bedrock-agent start-ingestion-job --knowledge-base-id <KB_ID> --data-source-id <DS_ID>
  EOF
  content_type = "text/plain"
}

resource "aws_s3_object" "fde_profiles_readme" {
  bucket       = aws_s3_bucket.knowledge_base_data.id
  key          = "fde-profiles/README.txt"
  content      = <<-EOF
    # FDE Profiles Data

    Upload your Field Development Engineer profile CSV files to this folder.

    Expected format:
    - name: FDE full name
    - email: FDE email address
    - slack_id: Slack user ID
    - expertise: Comma-separated expertise areas
    - certifications: Comma-separated certifications
    - years_experience: Years of experience
    - specializations: Primary specialization areas
    - past_tickets: Number of tickets resolved
    - success_rate: Success rate percentage

    After uploading new files, trigger Knowledge Base sync/ingestion via:
    aws bedrock-agent start-ingestion-job --knowledge-base-id <KB_ID> --data-source-id <DS_ID>
  EOF
  content_type = "text/plain"
}

# Output the bucket details
output "knowledge_base_bucket_name" {
  description = "Name of the S3 bucket for Knowledge Base data"
  value       = aws_s3_bucket.knowledge_base_data.id
}

output "knowledge_base_bucket_arn" {
  description = "ARN of the S3 bucket for Knowledge Base data"
  value       = aws_s3_bucket.knowledge_base_data.arn
}

output "tickets_data_path" {
  description = "S3 path for uploading ticket data"
  value       = "s3://${aws_s3_bucket.knowledge_base_data.id}/tickets/"
}

output "fde_profiles_data_path" {
  description = "S3 path for uploading FDE profile data"
  value       = "s3://${aws_s3_bucket.knowledge_base_data.id}/fde-profiles/"
}
