"""
Embedding Generator Lambda Handler

This Lambda function:
1. Triggered by S3 event when new ticket is uploaded
2. Reads ticket data from S3
3. Generates embeddings using AWS Bedrock Titan
4. Stores vectors in Pinecone with metadata
5. Triggers Step Functions workflow for SME matching
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

# Import shared utilities
import sys
sys.path.append('/opt/python')  # Lambda layer path
from shared.python.logging_config import get_logger
from shared.python.aws_clients import get_bedrock_runtime_client, get_s3_client, get_sfn_client
from shared.python.metrics import publish_metric
from shared.python.constants import (
    S3_BUCKET_TICKETS,
    BEDROCK_EMBEDDING_MODEL_ID,
    PINECONE_INDEX_NAME,
    STEP_FUNCTION_ARN
)

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for ticket content using Bedrock Titan"""

    def __init__(self):
        self.bedrock = get_bedrock_runtime_client()
        self.s3 = get_s3_client()
        self.sfn = get_sfn_client()
        self.model_id = BEDROCK_EMBEDDING_MODEL_ID

    def read_ticket_from_s3(self, bucket: str, key: str) -> Dict[str, Any]:
        """Read ticket data from S3"""
        try:
            response = self.s3.get_object(Bucket=bucket, Key=key)
            ticket_data = json.loads(response['Body'].read().decode('utf-8'))

            logger.info("Successfully read ticket from S3", extra={
                "bucket": bucket,
                "key": key,
                "ticket_id": ticket_data.get('ticket_id')
            })

            return ticket_data

        except ClientError as e:
            logger.error("Failed to read ticket from S3", extra={
                "error": str(e),
                "bucket": bucket,
                "key": key
            })
            raise

    def prepare_embedding_text(self, ticket_data: Dict[str, Any]) -> str:
        """
        Prepare comprehensive text for embedding generation.
        Combines multiple ticket fields for rich semantic representation.
        """
        ticket = ticket_data.get('ticket', {})
        comments = ticket_data.get('comments', [])

        # Extract key fields
        ticket_id = ticket.get('id', 'unknown')
        customer = ticket_data.get('customer_name', 'Unknown')
        priority = ticket.get('priority', 'normal')
        subject = ticket.get('subject', '')
        description = ticket.get('description', '')
        tags = ', '.join(ticket.get('tags', []))

        # Get last 5 comments for context
        recent_comments = []
        for comment in comments[-5:]:
            author = comment.get('author_name', 'Unknown')
            body = comment.get('body', '')
            recent_comments.append(f"{author}: {body}")

        conversation_history = '\n'.join(recent_comments)

        # Construct comprehensive embedding text
        embedding_text = f"""
Ticket ID: {ticket_id}
Customer: {customer}
Priority: {priority}
Subject: {subject}
Description: {description}
Tags: {tags}
Recent Conversation:
{conversation_history}
        """.strip()

        logger.info("Prepared embedding text", extra={
            "ticket_id": ticket_id,
            "text_length": len(embedding_text),
            "num_comments": len(comments)
        })

        return embedding_text

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using Bedrock Titan Embeddings.
        Returns a 1024-dimensional vector.
        """
        try:
            # Prepare request for Bedrock
            request_body = {
                "inputText": text
            }

            # Invoke Bedrock model
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                contentType='application/json',
                accept='application/json',
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding', [])

            # Track metrics
            input_tokens = response_body.get('inputTextTokenCount', 0)
            publish_metric(
                namespace='EmbeddingGenerator',
                metric_name='BedrockTokensUsed',
                value=input_tokens,
                unit='Count'
            )

            logger.info("Successfully generated embedding", extra={
                "embedding_dimension": len(embedding),
                "input_tokens": input_tokens,
                "model_id": self.model_id
            })

            return embedding

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'ThrottlingException':
                logger.warning("Bedrock throttling encountered, will retry")
                publish_metric(
                    namespace='EmbeddingGenerator',
                    metric_name='BedrockThrottling',
                    value=1,
                    unit='Count'
                )

            logger.error("Failed to generate embedding", extra={
                "error": str(e),
                "error_code": error_code
            })
            raise

    def store_in_pinecone(self, ticket_data: Dict[str, Any], embedding: List[float]) -> None:
        """
        Store embedding in Pinecone with metadata.
        Note: Pinecone client initialization happens here.
        """
        try:
            from pinecone import Pinecone

            # Initialize Pinecone
            pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])
            index = pc.Index(PINECONE_INDEX_NAME)

            ticket = ticket_data.get('ticket', {})
            ticket_id = str(ticket.get('id', 'unknown'))

            # Prepare metadata
            metadata = {
                "ticket_id": ticket_id,
                "customer_id": ticket_data.get('customer_id', 'unknown'),
                "customer_name": ticket_data.get('customer_name', 'Unknown'),
                "priority": ticket.get('priority', 'normal'),
                "created_at": ticket.get('created_at', datetime.utcnow().isoformat()),
                "tags": ticket.get('tags', []),
                "subject": ticket.get('subject', '')[:200],  # Truncate for metadata
                "cre_id": ticket_data.get('cre_id', 'unknown'),
                "resolution_success": False,  # Will be updated via feedback
                "timestamp": datetime.utcnow().isoformat()
            }

            # Upsert to Pinecone
            index.upsert(
                vectors=[{
                    "id": f"ticket-{ticket_id}",
                    "values": embedding,
                    "metadata": metadata
                }],
                namespace="tickets"
            )

            logger.info("Successfully stored embedding in Pinecone", extra={
                "ticket_id": ticket_id,
                "index_name": PINECONE_INDEX_NAME,
                "namespace": "tickets"
            })

            publish_metric(
                namespace='EmbeddingGenerator',
                metric_name='PineconeUpsertSuccess',
                value=1,
                unit='Count'
            )

        except Exception as e:
            logger.error("Failed to store in Pinecone", extra={
                "error": str(e),
                "ticket_id": ticket_data.get('ticket', {}).get('id')
            })

            publish_metric(
                namespace='EmbeddingGenerator',
                metric_name='PineconeUpsertFailure',
                value=1,
                unit='Count'
            )
            raise

    def trigger_step_function(self, ticket_data: Dict[str, Any]) -> str:
        """Trigger Step Functions workflow for SME matching"""
        try:
            ticket_id = ticket_data.get('ticket', {}).get('id', 'unknown')

            # Prepare Step Function input
            sfn_input = {
                "ticket_id": str(ticket_id),
                "bucket": S3_BUCKET_TICKETS,
                "key": ticket_data.get('s3_key', ''),
                "embedding_exists": True,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Start execution
            response = self.sfn.start_execution(
                stateMachineArn=STEP_FUNCTION_ARN,
                name=f"sme-match-{ticket_id}-{int(datetime.utcnow().timestamp())}",
                input=json.dumps(sfn_input)
            )

            execution_arn = response['executionArn']

            logger.info("Successfully triggered Step Function", extra={
                "ticket_id": ticket_id,
                "execution_arn": execution_arn
            })

            publish_metric(
                namespace='EmbeddingGenerator',
                metric_name='StepFunctionTriggered',
                value=1,
                unit='Count'
            )

            return execution_arn

        except ClientError as e:
            logger.error("Failed to trigger Step Function", extra={
                "error": str(e),
                "ticket_id": ticket_data.get('ticket', {}).get('id')
            })
            raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for S3 event trigger.

    Event structure:
    {
        "Records": [{
            "s3": {
                "bucket": {"name": "bucket-name"},
                "object": {"key": "path/to/ticket.json"}
            }
        }]
    }
    """
    start_time = datetime.utcnow()

    try:
        # Parse S3 event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        logger.info("Embedding generation started", extra={
            "bucket": bucket,
            "key": key,
            "request_id": context.request_id
        })

        # Initialize generator
        generator = EmbeddingGenerator()

        # Step 1: Read ticket from S3
        ticket_data = generator.read_ticket_from_s3(bucket, key)
        ticket_data['s3_key'] = key  # Store for later use

        # Step 2: Prepare embedding text
        embedding_text = generator.prepare_embedding_text(ticket_data)

        # Step 3: Generate embedding
        embedding = generator.generate_embedding(embedding_text)

        # Step 4: Store in Pinecone
        generator.store_in_pinecone(ticket_data, embedding)

        # Step 5: Trigger Step Function
        execution_arn = generator.trigger_step_function(ticket_data)

        # Calculate duration
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        publish_metric(
            namespace='EmbeddingGenerator',
            metric_name='ProcessingDuration',
            value=duration_ms,
            unit='Milliseconds'
        )

        publish_metric(
            namespace='EmbeddingGenerator',
            metric_name='Success',
            value=1,
            unit='Count'
        )

        logger.info("Embedding generation completed successfully", extra={
            "ticket_id": ticket_data.get('ticket', {}).get('id'),
            "duration_ms": duration_ms,
            "execution_arn": execution_arn
        })

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Embedding generated successfully',
                'ticket_id': ticket_data.get('ticket', {}).get('id'),
                'execution_arn': execution_arn
            })
        }

    except Exception as e:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.error("Embedding generation failed", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_ms": duration_ms
        }, exc_info=True)

        publish_metric(
            namespace='EmbeddingGenerator',
            metric_name='Failure',
            value=1,
            unit='Count'
        )

        # Re-raise to trigger Lambda retry
        raise
