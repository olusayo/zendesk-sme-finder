"""
Shared utilities package for Zendesk SME Finder.

This package contains reusable modules for AWS clients, logging,
metrics, and configuration.
"""

from .aws_clients import AWSClients, aws_clients, get_secret
from .logging_config import StructuredLogger, with_logging
from .metrics import MetricsCollector, metrics_collector, track_latency
from .constants import (
    AWS_REGION,
    BEDROCK_MODEL_ID,
    BEDROCK_EMBEDDING_MODEL_ID,
    PINECONE_INDEX_NAME,
    S3_BUCKET_TICKETS,
    S3_BUCKET_CRE_DATA,
    Environment,
    MetricNamespace,
    MetricName
)

__all__ = [
    # AWS Clients
    "AWSClients",
    "aws_clients",
    "get_secret",

    # Logging
    "StructuredLogger",
    "with_logging",

    # Metrics
    "MetricsCollector",
    "metrics_collector",
    "track_latency",

    # Constants
    "AWS_REGION",
    "BEDROCK_MODEL_ID",
    "BEDROCK_EMBEDDING_MODEL_ID",
    "PINECONE_INDEX_NAME",
    "S3_BUCKET_TICKETS",
    "S3_BUCKET_CRE_DATA",
    "Environment",
    "MetricNamespace",
    "MetricName"
]
