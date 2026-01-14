"""
CloudWatch metrics helper for tracking business and operational KPIs.

This module provides a clean interface for publishing metrics without
cluttering business logic code.
"""

from datetime import datetime
from typing import Optional, List, Dict
from functools import wraps

from aws_clients import put_cloudwatch_metric
from constants import (
    MetricNamespace,
    MetricName,
    ENABLE_COST_TRACKING,
    ENVIRONMENT
)
from logging_config import StructuredLogger

logger = StructuredLogger(__name__)


class MetricsCollector:
    """
    Collects and publishes CloudWatch metrics with automatic dimensioning.

    Usage:
        metrics = MetricsCollector()
        metrics.record_ticket_ingested(ticket_id="12345")
        metrics.record_latency("RAGPipeline", duration_ms=1234)
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.default_dimensions = [
            {"Name": "Environment", "Value": ENVIRONMENT}
        ]

    def _publish_metric(
        self,
        name: str,
        value: float,
        namespace: str,
        unit: str = "None",
        dimensions: Optional[List[Dict]] = None
    ):
        """
        Internal method to publish metric with default dimensions.

        Args:
            name: Metric name
            value: Metric value
            namespace: CloudWatch namespace
            unit: Metric unit
            dimensions: Additional dimensions (merged with defaults)
        """
        all_dimensions = self.default_dimensions.copy()
        if dimensions:
            all_dimensions.extend(dimensions)

        put_cloudwatch_metric(
            metric_name=name,
            value=value,
            namespace=namespace,
            dimensions=all_dimensions,
            unit=unit
        )

    # ========================================================================
    # Pipeline Metrics
    # ========================================================================

    def record_ticket_ingested(self, ticket_id: str, customer_id: str):
        """Record ticket ingestion event."""
        self._publish_metric(
            name=MetricName.TICKET_INGESTED.value,
            value=1,
            namespace=MetricNamespace.PIPELINE.value,
            unit="Count",
            dimensions=[
                {"Name": "TicketID", "Value": ticket_id},
                {"Name": "CustomerID", "Value": customer_id}
            ]
        )

    def record_embedding_generated(self, ticket_id: str, dimension: int):
        """Record embedding generation event."""
        self._publish_metric(
            name=MetricName.EMBEDDING_GENERATED.value,
            value=1,
            namespace=MetricNamespace.PIPELINE.value,
            unit="Count",
            dimensions=[
                {"Name": "TicketID", "Value": ticket_id},
                {"Name": "EmbeddingDimension", "Value": str(dimension)}
            ]
        )

    def record_rag_pipeline_success(self, ticket_id: str, num_smes_found: int):
        """Record successful RAG pipeline execution."""
        self._publish_metric(
            name=MetricName.RAG_PIPELINE_SUCCESS.value,
            value=1,
            namespace=MetricNamespace.PIPELINE.value,
            unit="Count",
            dimensions=[
                {"Name": "TicketID", "Value": ticket_id},
                {"Name": "SMEsFound", "Value": str(num_smes_found)}
            ]
        )

    def record_rag_pipeline_failure(self, ticket_id: str, error_type: str):
        """Record RAG pipeline failure."""
        self._publish_metric(
            name=MetricName.RAG_PIPELINE_FAILURE.value,
            value=1,
            namespace=MetricNamespace.PIPELINE.value,
            unit="Count",
            dimensions=[
                {"Name": "TicketID", "Value": ticket_id},
                {"Name": "ErrorType", "Value": error_type}
            ]
        )

    def record_slack_notification_sent(self, ticket_id: str, cre_id: str):
        """Record Slack notification sent."""
        self._publish_metric(
            name=MetricName.SLACK_NOTIFICATION_SENT.value,
            value=1,
            namespace=MetricNamespace.PIPELINE.value,
            unit="Count",
            dimensions=[
                {"Name": "TicketID", "Value": ticket_id},
                {"Name": "CREID", "Value": cre_id}
            ]
        )

    def record_latency(
        self,
        component: str,
        duration_ms: float,
        ticket_id: Optional[str] = None
    ):
        """
        Record component latency.

        Args:
            component: Component name (e.g., "TicketIngestion", "RAGPipeline")
            duration_ms: Duration in milliseconds
            ticket_id: Optional ticket ID for correlation
        """
        dimensions = [{"Name": "Component", "Value": component}]
        if ticket_id:
            dimensions.append({"Name": "TicketID", "Value": ticket_id})

        self._publish_metric(
            name=MetricName.END_TO_END_LATENCY.value,
            value=duration_ms,
            namespace=MetricNamespace.PIPELINE.value,
            unit="Milliseconds",
            dimensions=dimensions
        )

    def record_error_rate(self, component: str, error_rate_percent: float):
        """Record component error rate."""
        self._publish_metric(
            name=MetricName.ERROR_RATE.value,
            value=error_rate_percent,
            namespace=MetricNamespace.PIPELINE.value,
            unit="Percent",
            dimensions=[{"Name": "Component", "Value": component}]
        )

    # ========================================================================
    # Business Metrics
    # ========================================================================

    def record_sme_match_accuracy(
        self,
        ticket_id: str,
        was_helpful: bool,
        selected_rank: int
    ):
        """
        Record SME match accuracy based on CRE feedback.

        Args:
            ticket_id: Ticket ID
            was_helpful: Whether the SME was helpful (True/False)
            selected_rank: Which recommendation was selected (1, 2, or 3)
        """
        accuracy = 1.0 if was_helpful else 0.0

        self._publish_metric(
            name=MetricName.SME_MATCH_ACCURACY.value,
            value=accuracy,
            namespace=MetricNamespace.BUSINESS.value,
            unit="None",
            dimensions=[
                {"Name": "TicketID", "Value": ticket_id},
                {"Name": "SelectedRank", "Value": str(selected_rank)},
                {"Name": "WasHelpful", "Value": str(was_helpful)}
            ]
        )

    def record_average_confidence(
        self,
        ticket_id: str,
        confidence_score: float
    ):
        """Record average confidence score for recommendations."""
        self._publish_metric(
            name=MetricName.AVERAGE_CONFIDENCE.value,
            value=confidence_score,
            namespace=MetricNamespace.BUSINESS.value,
            unit="None",
            dimensions=[{"Name": "TicketID", "Value": ticket_id}]
        )

    def record_handoff_success(self, ticket_id: str, was_successful: bool):
        """Record whether handoff was successful."""
        success_value = 1.0 if was_successful else 0.0

        self._publish_metric(
            name=MetricName.HANDOFF_SUCCESS_RATE.value,
            value=success_value,
            namespace=MetricNamespace.BUSINESS.value,
            unit="None",
            dimensions=[
                {"Name": "TicketID", "Value": ticket_id},
                {"Name": "Successful", "Value": str(was_successful)}
            ]
        )

    def record_time_to_resolution(
        self,
        ticket_id: str,
        resolution_hours: float
    ):
        """Record time to resolution after SME handoff."""
        self._publish_metric(
            name=MetricName.TIME_TO_RESOLUTION.value,
            value=resolution_hours,
            namespace=MetricNamespace.BUSINESS.value,
            unit="None",
            dimensions=[{"Name": "TicketID", "Value": ticket_id}]
        )

    def record_cre_satisfaction(
        self,
        ticket_id: str,
        satisfaction_score: int  # 1-5 scale
    ):
        """Record CRE satisfaction score."""
        self._publish_metric(
            name=MetricName.CRE_SATISFACTION.value,
            value=float(satisfaction_score),
            namespace=MetricNamespace.BUSINESS.value,
            unit="None",
            dimensions=[{"Name": "TicketID", "Value": ticket_id}]
        )

    # ========================================================================
    # Cost Metrics
    # ========================================================================

    def record_bedrock_tokens(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float
    ):
        """
        Record Bedrock token usage and cost.

        Args:
            model_id: Bedrock model ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Estimated cost in USD
        """
        if not ENABLE_COST_TRACKING:
            return

        total_tokens = input_tokens + output_tokens

        self._publish_metric(
            name=MetricName.BEDROCK_TOKENS_CONSUMED.value,
            value=total_tokens,
            namespace=MetricNamespace.COST.value,
            unit="Count",
            dimensions=[
                {"Name": "ModelID", "Value": model_id},
                {"Name": "TokenType", "Value": "Total"}
            ]
        )

        self._publish_metric(
            name=MetricName.BEDROCK_COST_USD.value,
            value=cost_usd,
            namespace=MetricNamespace.COST.value,
            unit="None",
            dimensions=[{"Name": "ModelID", "Value": model_id}]
        )

    def record_pinecone_queries(self, num_queries: int, cost_estimate_usd: float):
        """Record Pinecone query count and estimated cost."""
        if not ENABLE_COST_TRACKING:
            return

        self._publish_metric(
            name=MetricName.PINECONE_QUERIES.value,
            value=num_queries,
            namespace=MetricNamespace.COST.value,
            unit="Count"
        )

    def record_lambda_invocation(self, function_name: str, duration_ms: float):
        """Record Lambda invocation for cost tracking."""
        if not ENABLE_COST_TRACKING:
            return

        self._publish_metric(
            name=MetricName.LAMBDA_INVOCATIONS.value,
            value=1,
            namespace=MetricNamespace.COST.value,
            unit="Count",
            dimensions=[
                {"Name": "FunctionName", "Value": function_name},
                {"Name": "DurationMS", "Value": str(int(duration_ms))}
            ]
        )

    def record_ecs_runtime(self, task_name: str, runtime_hours: float):
        """Record ECS task runtime for cost tracking."""
        if not ENABLE_COST_TRACKING:
            return

        self._publish_metric(
            name=MetricName.ECS_RUNTIME_HOURS.value,
            value=runtime_hours,
            namespace=MetricNamespace.COST.value,
            unit="None",
            dimensions=[{"Name": "TaskName", "Value": task_name}]
        )


# ============================================================================
# Decorator for Automatic Latency Tracking
# ============================================================================

def track_latency(component_name: str):
    """
    Decorator to automatically track function execution latency.

    Usage:
        @track_latency("TicketIngestion")
        def ingest_ticket(ticket_id):
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metrics = MetricsCollector()
            start_time = datetime.utcnow()

            try:
                result = func(*args, **kwargs)

                # Calculate latency
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                # Extract ticket_id if available in args or kwargs
                ticket_id = kwargs.get('ticket_id') or (args[0] if args else None)

                metrics.record_latency(
                    component=component_name,
                    duration_ms=duration_ms,
                    ticket_id=ticket_id if isinstance(ticket_id, str) else None
                )

                return result

            except Exception as e:
                # Still record latency even on failure
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                metrics.record_latency(
                    component=component_name,
                    duration_ms=duration_ms
                )
                raise

        return wrapper
    return decorator


# ============================================================================
# Global Instance
# ============================================================================

# Pre-initialize metrics collector for Lambda warm starts
metrics_collector = MetricsCollector()
