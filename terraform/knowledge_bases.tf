# Bedrock Knowledge Bases
# Creates Knowledge Bases for similar tickets and FDE profiles

# Tickets Knowledge Base
resource "aws_bedrockagent_knowledge_base" "tickets" {
  name        = "${var.project_name}-tickets-kb"
  description = "Historical Zendesk tickets with resolutions for similarity search"
  role_arn    = aws_iam_role.knowledge_base_tickets.arn

  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/amazon.titan-embed-text-v2:0"
    }
    type = "VECTOR"
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.tickets_kb.arn
      vector_index_name = "bedrock-knowledge-base-tickets-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-tickets-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }

  depends_on = [
    aws_opensearchserverless_collection.tickets_kb,
    aws_opensearchserverless_access_policy.knowledge_base_data_access
  ]

  tags = {
    Name        = "${var.project_name}-tickets-knowledge-base"
    Description = "Historical tickets for similarity matching"
  }
}

# Tickets Data Source
resource "aws_bedrockagent_data_source" "tickets" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.tickets.id
  name              = "${var.project_name}-tickets-data-source"
  description       = "S3 data source for historical ticket CSV files"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.knowledge_base_data.arn
      inclusion_prefixes = [
        var.tickets_s3_prefix
      ]
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }

  depends_on = [
    aws_s3_bucket.knowledge_base_data,
    aws_bedrockagent_knowledge_base.tickets
  ]
}

# FDE Profiles Knowledge Base
resource "aws_bedrockagent_knowledge_base" "fde_profiles" {
  name        = "${var.project_name}-fde-profiles-kb"
  description = "FDE expertise profiles and certifications for expert matching"
  role_arn    = aws_iam_role.knowledge_base_fde_profiles.arn

  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/amazon.titan-embed-text-v2:0"
    }
    type = "VECTOR"
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.fde_profiles_kb.arn
      vector_index_name = "bedrock-knowledge-base-fde-profiles-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-fde-profiles-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }

  depends_on = [
    aws_opensearchserverless_collection.fde_profiles_kb,
    aws_opensearchserverless_access_policy.knowledge_base_data_access
  ]

  tags = {
    Name        = "${var.project_name}-fde-profiles-knowledge-base"
    Description = "FDE expertise profiles for matching"
  }
}

# FDE Profiles Data Source
resource "aws_bedrockagent_data_source" "fde_profiles" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.fde_profiles.id
  name              = "${var.project_name}-fde-profiles-data-source"
  description       = "S3 data source for FDE profile CSV files"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.knowledge_base_data.arn
      inclusion_prefixes = [
        var.certificates_s3_prefix
      ]
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }

  depends_on = [
    aws_s3_bucket.knowledge_base_data,
    aws_bedrockagent_knowledge_base.fde_profiles
  ]
}

# Outputs
output "tickets_knowledge_base_id" {
  description = "ID of the Tickets Knowledge Base"
  value       = aws_bedrockagent_knowledge_base.tickets.id
}

output "tickets_knowledge_base_arn" {
  description = "ARN of the Tickets Knowledge Base"
  value       = aws_bedrockagent_knowledge_base.tickets.arn
}

output "tickets_data_source_id" {
  description = "ID of the Tickets data source"
  value       = aws_bedrockagent_data_source.tickets.data_source_id
}

output "fde_profiles_knowledge_base_id" {
  description = "ID of the FDE Profiles Knowledge Base"
  value       = aws_bedrockagent_knowledge_base.fde_profiles.id
}

output "fde_profiles_knowledge_base_arn" {
  description = "ARN of the FDE Profiles Knowledge Base"
  value       = aws_bedrockagent_knowledge_base.fde_profiles.arn
}

output "fde_profiles_data_source_id" {
  description = "ID of the FDE Profiles data source"
  value       = aws_bedrockagent_data_source.fde_profiles.data_source_id
}
