"""
Shared constants and configuration for Zendesk SME Finder.

This module centralizes all configuration values to ensure consistency
across Lambda functions and ECS tasks.
"""

import os
from enum import Enum


# ============================================================================
# AWS Configuration
# ============================================================================

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID")

# ============================================================================
# Bedrock Configuration
# ============================================================================

class BedrockModel(Enum):
    """Supported Bedrock models"""
    # Updated to use regional endpoint for on-demand throughput
    # Note: Use us.anthropic for US region, eu.anthropic for EU, apac.anthropic for APAC
    CLAUDE_SONNET_4_5 = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    TITAN_EMBEDDINGS_V2 = "amazon.titan-embed-text-v2:0"


BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", BedrockModel.CLAUDE_SONNET_4_5.value)
BEDROCK_EMBEDDING_MODEL_ID = os.getenv(
    "BEDROCK_EMBEDDING_MODEL_ID",
    BedrockModel.TITAN_EMBEDDINGS_V2.value
)
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "4096"))
BEDROCK_TEMPERATURE = float(os.getenv("BEDROCK_TEMPERATURE", "0.7"))

# Bedrock Error Handling Configuration
BEDROCK_REQUEST_TIMEOUT = int(os.getenv("BEDROCK_REQUEST_TIMEOUT", "60"))
BEDROCK_MAX_RETRIES = int(os.getenv("BEDROCK_MAX_RETRIES", "5"))
BEDROCK_BACKOFF_MULTIPLIER = float(os.getenv("BEDROCK_BACKOFF_MULTIPLIER", "2.0"))
BEDROCK_BACKOFF_MAX = int(os.getenv("BEDROCK_BACKOFF_MAX", "32"))

# Titan Embeddings Configuration
TITAN_EMBEDDING_DIMENSION = int(os.getenv("TITAN_EMBEDDING_DIMENSION", "1024"))  # 256, 512, or 1024
TITAN_NORMALIZE = os.getenv("TITAN_NORMALIZE", "true").lower() == "true"

# ============================================================================
# Pinecone Configuration
# ============================================================================

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "zendesk-sme-finder")
PINECONE_DIMENSION = int(os.getenv("PINECONE_DIMENSION", "1024"))
PINECONE_METRIC = os.getenv("PINECONE_METRIC", "cosine")

# Pinecone Namespaces
class PineconeNamespace(Enum):
    """Pinecone index namespaces for organizing vectors"""
    TICKETS = "tickets"
    CRE_PROFILES = "cre-profiles"
    HISTORICAL_RESOLUTIONS = "historical-resolutions"


# ============================================================================
# S3 Configuration
# ============================================================================

S3_BUCKET_TICKETS = os.getenv("S3_BUCKET_TICKETS", "zendesk-sme-tickets")
S3_BUCKET_CRE_DATA = os.getenv("S3_BUCKET_CRE_DATA", "zendesk-sme-cre-profiles")
S3_BUCKET_METADATA = os.getenv("S3_BUCKET_METADATA", "zendesk-sme-metadata")

# S3 Key Prefixes
class S3Prefix:
    """S3 key prefixes for organizing data"""
    RAW_TICKETS = "raw-tickets"
    PROCESSED_TICKETS = "processed"
    EMBEDDINGS_BACKUP = "embeddings-backup"
    CRE_CERTIFICATIONS = "certifications"
    HISTORICAL_RESOLUTIONS = "historical-resolutions"
    CRE_EMBEDDINGS = "embeddings"
    FEEDBACK = "feedback"
    METRICS = "metrics"
    MODEL_ARTIFACTS = "model-artifacts"


# ============================================================================
# Zendesk Configuration
# ============================================================================

ZENDESK_DOMAIN = os.getenv("ZENDESK_DOMAIN")
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
ZENDESK_WEBHOOK_SECRET = os.getenv("ZENDESK_WEBHOOK_SECRET")

# Zendesk Tag for triggering SME matching
ZENDESK_SME_TAG = "need_sme"
ZENDESK_RESOLVED_TAG = "sme_resolved"

# ============================================================================
# Slack Configuration
# ============================================================================

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_CHANNEL_HANDOFFS = os.getenv("SLACK_CHANNEL_HANDOFFS", "#sme-handoffs")
SLACK_ALERT_CHANNEL = os.getenv("SLACK_ALERT_CHANNEL", "#sme-alerts")

# ============================================================================
# Step Functions
# ============================================================================

STEP_FUNCTION_ARN = os.getenv("STEP_FUNCTION_ARN")

# ============================================================================
# Application Configuration
# ============================================================================

class Environment(Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


ENVIRONMENT = os.getenv("ENVIRONMENT", Environment.DEVELOPMENT.value)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_CONCURRENT_EXECUTIONS = int(os.getenv("MAX_CONCURRENT_EXECUTIONS", "10"))
RAG_TIMEOUT_SECONDS = int(os.getenv("RAG_TIMEOUT_SECONDS", "300"))

# ============================================================================
# Feature Flags
# ============================================================================

ENABLE_FEEDBACK_LOOP = os.getenv("ENABLE_FEEDBACK_LOOP", "true").lower() == "true"
ENABLE_COST_TRACKING = os.getenv("ENABLE_COST_TRACKING", "true").lower() == "true"
ENABLE_XRAY_TRACING = os.getenv("ENABLE_XRAY_TRACING", "true").lower() == "true"

# ============================================================================
# Performance Tuning
# ============================================================================

VECTOR_SEARCH_TOP_K = int(os.getenv("VECTOR_SEARCH_TOP_K", "20"))
MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.60"))
MAX_SME_RECOMMENDATIONS = int(os.getenv("MAX_SME_RECOMMENDATIONS", "3"))

# ============================================================================
# Cost Limits
# ============================================================================

DAILY_BEDROCK_TOKEN_LIMIT = int(os.getenv("DAILY_BEDROCK_TOKEN_LIMIT", "1000000"))
MONTHLY_BUDGET_USD = float(os.getenv("MONTHLY_BUDGET_USD", "100.0"))

# ============================================================================
# CloudWatch Metrics
# ============================================================================

class MetricNamespace(Enum):
    """CloudWatch metric namespaces"""
    SME_FINDER = "SMEFinder"
    PIPELINE = "SMEFinder/Pipeline"
    BUSINESS = "SMEFinder/Business"
    COST = "SMEFinder/Cost"


class MetricName(Enum):
    """CloudWatch metric names"""
    # Pipeline metrics
    TICKET_INGESTED = "TicketIngested"
    EMBEDDING_GENERATED = "EmbeddingGenerated"
    RAG_PIPELINE_SUCCESS = "RAGPipelineSuccess"
    RAG_PIPELINE_FAILURE = "RAGPipelineFailure"
    SLACK_NOTIFICATION_SENT = "SlackNotificationSent"
    END_TO_END_LATENCY = "EndToEndLatency"
    ERROR_RATE = "ErrorRate"

    # Business metrics
    SME_MATCH_ACCURACY = "SMEMatchAccuracy"
    AVERAGE_CONFIDENCE = "AverageConfidence"
    HANDOFF_SUCCESS_RATE = "HandoffSuccessRate"
    TIME_TO_RESOLUTION = "TimeToResolution"
    CRE_SATISFACTION = "CRESatisfaction"

    # Cost metrics
    BEDROCK_TOKENS_CONSUMED = "BedrockTokensConsumed"
    BEDROCK_COST_USD = "BedrockCostUSD"
    PINECONE_QUERIES = "PineconeQueries"
    LAMBDA_INVOCATIONS = "LambdaInvocations"
    ECS_RUNTIME_HOURS = "ECSRuntimeHours"


# ============================================================================
# Error Messages
# ============================================================================

class ErrorMessage(Enum):
    """Standardized error messages"""
    ZENDESK_API_ERROR = "Failed to fetch ticket from Zendesk API"
    BEDROCK_THROTTLED = "Bedrock API throttled, retrying with backoff"
    PINECONE_CONNECTION_ERROR = "Failed to connect to Pinecone"
    S3_UPLOAD_FAILED = "Failed to upload data to S3"
    INVALID_TICKET_FORMAT = "Ticket data validation failed"
    LOW_CONFIDENCE_MATCH = "SME match confidence below threshold"
    SLACK_API_ERROR = "Failed to send Slack notification"
    STEP_FUNCTION_ERROR = "Step Functions execution failed"


# ============================================================================
# Data Schemas
# ============================================================================

# CRE Profile CSV columns (already uploaded to S3)
CRE_PROFILE_COLUMNS = [
    "cre_id",
    "name",
    "email",
    "slack_id",
    "certifications",
    "specializations",
    "years_experience"
]

# Historical Resolutions CSV columns (already uploaded to S3)
HISTORICAL_RESOLUTION_COLUMNS = [
    "ticket_id",
    "customer_id",
    "issue_category",
    "assigned_cre",
    "resolution_success",
    "resolution_time_hours",
    "technologies_used"
]

# ============================================================================
# Validation Rules
# ============================================================================

MAX_TICKET_DESCRIPTION_LENGTH = 50000  # characters
MIN_TICKET_DESCRIPTION_LENGTH = 10  # characters
MAX_EMBEDDING_RETRIES = 3
MAX_BEDROCK_RETRIES = 3
EXPONENTIAL_BACKOFF_BASE = 2  # seconds


# ============================================================================
# Helper Functions
# ============================================================================

def get_s3_ticket_key(ticket_id: str, prefix: str = S3Prefix.RAW_TICKETS) -> str:
    """
    Generate S3 key for ticket storage with date partitioning.

    Args:
        ticket_id: Zendesk ticket ID
        prefix: S3 prefix (default: RAW_TICKETS)

    Returns:
        S3 key string with date partitioning
    """
    from datetime import datetime
    now = datetime.utcnow()
    return f"{prefix}/year={now.year}/month={now.month:02d}/day={now.day:02d}/ticket-{ticket_id}.json"


def get_feedback_key() -> str:
    """
    Generate S3 key for feedback data storage.

    Returns:
        S3 key string with date partitioning
    """
    from datetime import datetime
    now = datetime.utcnow()
    return f"{S3Prefix.FEEDBACK}/year={now.year}/month={now.month:02d}/feedback-data.jsonl"


def validate_environment_variables() -> list[str]:
    """
    Validate that all required environment variables are set.

    Returns:
        List of missing environment variable names (empty if all present)
    """
    required_vars = [
        "AWS_ACCOUNT_ID",
        "PINECONE_API_KEY",
        "ZENDESK_DOMAIN",
        "ZENDESK_API_TOKEN",
        "ZENDESK_EMAIL",
        "SLACK_BOT_TOKEN",
        "SLACK_SIGNING_SECRET"
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    return missing
