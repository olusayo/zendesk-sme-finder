"""
Ticket Ingestion Lambda Handler.

This Lambda function is triggered by Zendesk webhooks when a CRE flags
a ticket with the "need_sme" tag. It fetches the full ticket context,
stores it in S3, and triggers the embedding generation Lambda.

Event Source: Zendesk Webhook (API Gateway)
Output: S3 ticket storage + Lambda invocation
"""

import json
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any

# Import shared utilities (Lambda Layer)
import sys
sys.path.insert(0, '/opt/python')  # Lambda Layer path

from aws_clients import AWSClients, invoke_lambda
from logging_config import StructuredLogger, log_lambda_event
from metrics import MetricsCollector, track_latency
from constants import (
    ZENDESK_WEBHOOK_SECRET,
    S3_BUCKET_TICKETS,
    get_s3_ticket_key,
    ErrorMessage
)

from zendesk_client import ZendeskClient
from validator import validate_ticket_data


# Initialize clients
aws_clients = AWSClients()
metrics = MetricsCollector()
logger = StructuredLogger(__name__)


@track_latency("TicketIngestion")
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Zendesk ticket ingestion.

    Args:
        event: API Gateway event containing Zendesk webhook payload
        context: Lambda context

    Returns:
        API Gateway response dict
    """
    # Set up logging with context
    log_lambda_event(logger, event, context)

    try:
        # Step 1: Validate webhook signature
        if not validate_webhook_signature(event):
            logger.warning("Invalid webhook signature")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Invalid signature"})
            }

        # Step 2: Parse webhook payload
        webhook_payload = parse_webhook_payload(event)
        ticket_id = webhook_payload.get("ticket_id")

        if not ticket_id:
            logger.error("No ticket_id in webhook payload")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing ticket_id"})
            }

        logger.set_correlation_id(f"ticket-{ticket_id}")
        logger.info(f"Processing ticket ingestion for ticket_id: {ticket_id}")

        # Step 3: Fetch full ticket context from Zendesk
        zendesk_client = ZendeskClient()
        ticket_data = zendesk_client.get_ticket_with_context(ticket_id)

        # Step 4: Validate ticket data
        validation_errors = validate_ticket_data(ticket_data)
        if validation_errors:
            logger.error(
                "Ticket validation failed",
                extra={"ticket_id": ticket_id, "errors": validation_errors}
            )
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid ticket data", "details": validation_errors})
            }

        # Step 5: Store raw ticket in S3
        s3_key = get_s3_ticket_key(ticket_id)
        store_ticket_in_s3(ticket_data, s3_key)

        # Step 6: Trigger embedding generation Lambda
        embedding_lambda_payload = {
            "ticket_id": ticket_id,
            "s3_bucket": S3_BUCKET_TICKETS,
            "s3_key": s3_key,
            "customer_id": ticket_data.get("requester", {}).get("id"),
            "priority": ticket_data.get("priority")
        }

        invoke_lambda(
            function_name="embedding-generator",
            payload=embedding_lambda_payload,
            invocation_type="Event"  # Async invocation
        )

        # Step 7: Record metrics
        metrics.record_ticket_ingested(
            ticket_id=str(ticket_id),
            customer_id=str(ticket_data.get("requester", {}).get("id"))
        )

        logger.info(
            f"Successfully ingested ticket {ticket_id}",
            extra={
                "ticket_id": ticket_id,
                "s3_key": s3_key,
                "customer_id": ticket_data.get("requester", {}).get("id")
            }
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Ticket ingested successfully",
                "ticket_id": ticket_id,
                "s3_key": s3_key
            })
        }

    except Exception as e:
        logger.error(
            f"Failed to ingest ticket: {str(e)}",
            extra={"error_type": type(e).__name__}
        )

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e)
            })
        }


def validate_webhook_signature(event: Dict[str, Any]) -> bool:
    """
    Validate Zendesk webhook signature using HMAC-SHA256.

    Args:
        event: API Gateway event

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        headers = event.get("headers", {})
        signature = headers.get("X-Zendesk-Webhook-Signature") or headers.get("x-zendesk-webhook-signature")
        timestamp = headers.get("X-Zendesk-Webhook-Signature-Timestamp") or headers.get("x-zendesk-webhook-signature-timestamp")

        if not signature or not timestamp:
            logger.warning("Missing signature or timestamp in webhook")
            return False

        # Reconstruct the signing string
        body = event.get("body", "")
        signing_string = timestamp + body

        # Calculate expected signature
        expected_signature = hmac.new(
            key=ZENDESK_WEBHOOK_SECRET.encode('utf-8'),
            msg=signing_string.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Compare signatures
        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            logger.warning(
                "Webhook signature mismatch",
                extra={"expected": expected_signature[:8], "received": signature[:8]}
            )

        return is_valid

    except Exception as e:
        logger.error(f"Error validating webhook signature: {str(e)}")
        return False


def parse_webhook_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Zendesk webhook payload from API Gateway event.

    Args:
        event: API Gateway event

    Returns:
        Parsed webhook payload dict
    """
    body = event.get("body", "{}")

    # Handle base64 encoding from API Gateway
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode('utf-8')

    payload = json.loads(body)

    # Zendesk webhook payload structure
    # {"ticket_id": 12345, "tag_added": "need_sme", ...}
    return payload


def store_ticket_in_s3(ticket_data: Dict[str, Any], s3_key: str):
    """
    Store raw ticket data in S3 with metadata.

    Args:
        ticket_data: Full ticket context from Zendesk
        s3_key: S3 key for storage
    """
    try:
        # Add processing metadata
        ticket_data["_metadata"] = {
            "ingested_at": datetime.utcnow().isoformat() + "Z",
            "source": "zendesk_webhook",
            "version": "1.0"
        }

        # Upload to S3
        aws_clients.s3.put_object(
            Bucket=S3_BUCKET_TICKETS,
            Key=s3_key,
            Body=json.dumps(ticket_data, indent=2),
            ContentType="application/json",
            Metadata={
                "ticket_id": str(ticket_data.get("id")),
                "customer_id": str(ticket_data.get("requester", {}).get("id")),
                "priority": ticket_data.get("priority", "unknown")
            }
        )

        logger.info(
            f"Stored ticket in S3: {s3_key}",
            extra={"s3_bucket": S3_BUCKET_TICKETS, "s3_key": s3_key}
        )

    except Exception as e:
        logger.error(
            f"Failed to store ticket in S3: {str(e)}",
            extra={"s3_key": s3_key, "error": str(e)}
        )
        raise
