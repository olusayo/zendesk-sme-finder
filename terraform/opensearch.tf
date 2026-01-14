# OpenSearch Serverless Collections for Knowledge Bases
# Used by Bedrock Knowledge Bases for vector storage and similarity search

# Encryption policy for OpenSearch Serverless collections
resource "aws_opensearchserverless_security_policy" "knowledge_base_encryption" {
  name = "${var.project_name}-kb-encryption"
  type = "encryption"
  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/${var.project_name}-tickets-kb",
          "collection/${var.project_name}-fde-profiles-kb"
        ]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

# Network policy for OpenSearch Serverless collections
resource "aws_opensearchserverless_security_policy" "knowledge_base_network" {
  name = "${var.project_name}-kb-network"
  type = "network"
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.project_name}-tickets-kb",
            "collection/${var.project_name}-fde-profiles-kb"
          ]
          ResourceType = "collection"
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# Data access policy for OpenSearch Serverless collections
resource "aws_opensearchserverless_access_policy" "knowledge_base_data_access" {
  name = "${var.project_name}-kb-data-access"
  type = "data"
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.project_name}-tickets-kb",
            "collection/${var.project_name}-fde-profiles-kb"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "index/${var.project_name}-tickets-kb/*",
            "index/${var.project_name}-fde-profiles-kb/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
          ResourceType = "index"
        }
      ]
      Principal = [
        aws_iam_role.knowledge_base_tickets.arn,
        aws_iam_role.knowledge_base_fde_profiles.arn
      ]
    }
  ])
}

# OpenSearch Serverless collection for Tickets Knowledge Base
resource "aws_opensearchserverless_collection" "tickets_kb" {
  name = "${var.project_name}-tickets-kb"
  type = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.knowledge_base_encryption,
    aws_opensearchserverless_security_policy.knowledge_base_network
  ]

  tags = {
    Name        = "${var.project_name}-tickets-knowledge-base"
    Description = "Vector search collection for historical tickets"
  }
}

# OpenSearch Serverless collection for FDE Profiles Knowledge Base
resource "aws_opensearchserverless_collection" "fde_profiles_kb" {
  name = "${var.project_name}-fde-profiles-kb"
  type = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.knowledge_base_encryption,
    aws_opensearchserverless_security_policy.knowledge_base_network
  ]

  tags = {
    Name        = "${var.project_name}-fde-profiles-knowledge-base"
    Description = "Vector search collection for FDE expertise profiles"
  }
}

# IAM role for Tickets Knowledge Base
resource "aws_iam_role" "knowledge_base_tickets" {
  name = "${var.project_name}-kb-tickets-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-kb-tickets-role"
  }
}

# IAM role for FDE Profiles Knowledge Base
resource "aws_iam_role" "knowledge_base_fde_profiles" {
  name = "${var.project_name}-kb-fde-profiles-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-kb-fde-profiles-role"
  }
}

# Policy for Tickets Knowledge Base to access S3 and OpenSearch
resource "aws_iam_role_policy" "knowledge_base_tickets_policy" {
  name = "${var.project_name}-kb-tickets-policy"
  role = aws_iam_role.knowledge_base_tickets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ListBucketStatement"
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.knowledge_base_data.arn
        ]
        Condition = {
          StringEquals = {
            "aws:ResourceAccount" = [
              data.aws_caller_identity.current.account_id
            ]
          }
        }
      },
      {
        Sid    = "S3GetObjectStatement"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.knowledge_base_data.arn}/tickets/*"
        ]
        Condition = {
          StringEquals = {
            "aws:ResourceAccount" = [
              data.aws_caller_identity.current.account_id
            ]
          }
        }
      },
      {
        Sid    = "BedrockInvokeModelStatement"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/amazon.titan-embed-text-v2:0"
        ]
      },
      {
        Sid    = "OpenSearchServerlessAPIAccessStatement"
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = [
          aws_opensearchserverless_collection.tickets_kb.arn
        ]
      }
    ]
  })
}

# Policy for FDE Profiles Knowledge Base to access S3 and OpenSearch
resource "aws_iam_role_policy" "knowledge_base_fde_profiles_policy" {
  name = "${var.project_name}-kb-fde-profiles-policy"
  role = aws_iam_role.knowledge_base_fde_profiles.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ListBucketStatement"
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.knowledge_base_data.arn
        ]
        Condition = {
          StringEquals = {
            "aws:ResourceAccount" = [
              data.aws_caller_identity.current.account_id
            ]
          }
        }
      },
      {
        Sid    = "S3GetObjectStatement"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.knowledge_base_data.arn}/fde-profiles/*"
        ]
        Condition = {
          StringEquals = {
            "aws:ResourceAccount" = [
              data.aws_caller_identity.current.account_id
            ]
          }
        }
      },
      {
        Sid    = "BedrockInvokeModelStatement"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/amazon.titan-embed-text-v2:0"
        ]
      },
      {
        Sid    = "OpenSearchServerlessAPIAccessStatement"
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = [
          aws_opensearchserverless_collection.fde_profiles_kb.arn
        ]
      }
    ]
  })
}

# Outputs
output "opensearch_tickets_collection_arn" {
  description = "ARN of the OpenSearch Serverless collection for tickets"
  value       = aws_opensearchserverless_collection.tickets_kb.arn
}

output "opensearch_tickets_collection_endpoint" {
  description = "Endpoint of the OpenSearch Serverless collection for tickets"
  value       = aws_opensearchserverless_collection.tickets_kb.collection_endpoint
}

output "opensearch_fde_profiles_collection_arn" {
  description = "ARN of the OpenSearch Serverless collection for FDE profiles"
  value       = aws_opensearchserverless_collection.fde_profiles_kb.arn
}

output "opensearch_fde_profiles_collection_endpoint" {
  description = "Endpoint of the OpenSearch Serverless collection for FDE profiles"
  value       = aws_opensearchserverless_collection.fde_profiles_kb.collection_endpoint
}

output "knowledge_base_tickets_role_arn" {
  description = "ARN of the IAM role for Tickets Knowledge Base"
  value       = aws_iam_role.knowledge_base_tickets.arn
}

output "knowledge_base_fde_profiles_role_arn" {
  description = "ARN of the IAM role for FDE Profiles Knowledge Base"
  value       = aws_iam_role.knowledge_base_fde_profiles.arn
}
