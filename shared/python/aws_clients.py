"""
Centralized AWS client management with connection pooling and retry logic.

This module provides pre-configured boto3 clients for all AWS services
used in the SME Finder system, with proper error handling and retries.
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional
import json

from constants import AWS_REGION, ENABLE_XRAY_TRACING
from logging_config import StructuredLogger

logger = StructuredLogger(__name__)


# ============================================================================
# Boto3 Configuration
# ============================================================================

# Standard retry configuration with exponential backoff
RETRY_CONFIG = Config(
    region_name=AWS_REGION,
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'  # Adaptive retry mode for better resilience
    },
    max_pool_connections=50,  # Connection pooling for Lambda/ECS
    connect_timeout=5,
    read_timeout=60
)


# ============================================================================
# Client Initialization
# ============================================================================

class AWSClients:
    """
    Singleton class for managing AWS service clients with connection pooling.

    Usage:
        clients = AWSClients()
        response = clients.s3.put_object(Bucket="my-bucket", Key="key", Body=data)
    """

    _instance = None
    _clients = {}

    def __new__(cls):
        """Singleton pattern to reuse clients across Lambda invocations."""
        if cls._instance is None:
            cls._instance = super(AWSClients, cls).__new__(cls)
        return cls._instance

    @property
    def s3(self):
        """Get or create S3 client."""
        if 's3' not in self._clients:
            self._clients['s3'] = boto3.client('s3', config=RETRY_CONFIG)
            logger.debug("Initialized S3 client")
        return self._clients['s3']

    @property
    def bedrock_runtime(self):
        """Get or create Bedrock Runtime client."""
        if 'bedrock_runtime' not in self._clients:
            self._clients['bedrock_runtime'] = boto3.client(
                'bedrock-runtime',
                config=RETRY_CONFIG
            )
            logger.debug("Initialized Bedrock Runtime client")
        return self._clients['bedrock_runtime']

    @property
    def stepfunctions(self):
        """Get or create Step Functions client."""
        if 'stepfunctions' not in self._clients:
            self._clients['stepfunctions'] = boto3.client(
                'stepfunctions',
                config=RETRY_CONFIG
            )
            logger.debug("Initialized Step Functions client")
        return self._clients['stepfunctions']

    @property
    def secretsmanager(self):
        """Get or create Secrets Manager client."""
        if 'secretsmanager' not in self._clients:
            self._clients['secretsmanager'] = boto3.client(
                'secretsmanager',
                config=RETRY_CONFIG
            )
            logger.debug("Initialized Secrets Manager client")
        return self._clients['secretsmanager']

    @property
    def cloudwatch(self):
        """Get or create CloudWatch client."""
        if 'cloudwatch' not in self._clients:
            self._clients['cloudwatch'] = boto3.client(
                'cloudwatch',
                config=RETRY_CONFIG
            )
            logger.debug("Initialized CloudWatch client")
        return self._clients['cloudwatch']

    @property
    def lambda_client(self):
        """Get or create Lambda client."""
        if 'lambda' not in self._clients:
            self._clients['lambda'] = boto3.client(
                'lambda',
                config=RETRY_CONFIG
            )
            logger.debug("Initialized Lambda client")
        return self._clients['lambda']


# ============================================================================
# Helper Functions
# ============================================================================

def get_secret(secret_name: str, aws_clients: Optional[AWSClients] = None) -> dict:
    """
    Retrieve secret from AWS Secrets Manager.

    Args:
        secret_name: Name of the secret
        aws_clients: Optional AWSClients instance (creates new if not provided)

    Returns:
        Dict containing secret key-value pairs

    Raises:
        ClientError: If secret retrieval fails
    """
    if aws_clients is None:
        aws_clients = AWSClients()

    try:
        logger.info(f"Retrieving secret: {secret_name}")

        response = aws_clients.secretsmanager.get_secret_value(
            SecretId=secret_name
        )

        # Parse the secret string (stored as JSON)
        secret_dict = json.loads(response['SecretString'])

        logger.info(f"Successfully retrieved secret: {secret_name}")
        return secret_dict

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(
            f"Failed to retrieve secret: {secret_name}",
            extra={
                "secret_name": secret_name,
                "error_code": error_code
            }
        )
        raise


def put_cloudwatch_metric(
    metric_name: str,
    value: float,
    namespace: str,
    dimensions: Optional[list[dict]] = None,
    unit: str = "None",
    aws_clients: Optional[AWSClients] = None
):
    """
    Publish custom metric to CloudWatch.

    Args:
        metric_name: Metric name
        value: Metric value
        namespace: CloudWatch namespace
        dimensions: List of dimension dicts [{"Name": "x", "Value": "y"}]
        unit: Metric unit (Seconds, Count, Bytes, etc.)
        aws_clients: Optional AWSClients instance

    Example:
        put_cloudwatch_metric(
            metric_name="TicketProcessed",
            value=1,
            namespace="SMEFinder",
            dimensions=[{"Name": "Environment", "Value": "production"}],
            unit="Count"
        )
    """
    if aws_clients is None:
        aws_clients = AWSClients()

    try:
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit
        }

        if dimensions:
            metric_data['Dimensions'] = dimensions

        aws_clients.cloudwatch.put_metric_data(
            Namespace=namespace,
            MetricData=[metric_data]
        )

        logger.debug(
            f"Published CloudWatch metric: {metric_name}",
            extra={
                "metric_name": metric_name,
                "value": value,
                "namespace": namespace
            }
        )

    except ClientError as e:
        logger.warning(
            f"Failed to publish CloudWatch metric: {metric_name}",
            extra={
                "metric_name": metric_name,
                "error": str(e)
            }
        )
        # Don't raise - metrics publishing should not break main flow


def start_step_function_execution(
    state_machine_arn: str,
    input_data: dict,
    execution_name: Optional[str] = None,
    aws_clients: Optional[AWSClients] = None
) -> str:
    """
    Start Step Functions execution.

    Args:
        state_machine_arn: ARN of the state machine
        input_data: Input data for the execution (will be JSON serialized)
        execution_name: Optional execution name (auto-generated if not provided)
        aws_clients: Optional AWSClients instance

    Returns:
        Execution ARN

    Raises:
        ClientError: If execution start fails
    """
    if aws_clients is None:
        aws_clients = AWSClients()

    try:
        params = {
            'stateMachineArn': state_machine_arn,
            'input': json.dumps(input_data)
        }

        if execution_name:
            params['name'] = execution_name

        response = aws_clients.stepfunctions.start_execution(**params)

        execution_arn = response['executionArn']

        logger.info(
            "Started Step Functions execution",
            extra={
                "state_machine_arn": state_machine_arn,
                "execution_arn": execution_arn,
                "execution_name": execution_name
            }
        )

        return execution_arn

    except ClientError as e:
        logger.error(
            "Failed to start Step Functions execution",
            extra={
                "state_machine_arn": state_machine_arn,
                "error": str(e)
            }
        )
        raise


def invoke_lambda(
    function_name: str,
    payload: dict,
    invocation_type: str = "Event",  # Event = async, RequestResponse = sync
    aws_clients: Optional[AWSClients] = None
) -> Optional[dict]:
    """
    Invoke Lambda function.

    Args:
        function_name: Lambda function name or ARN
        payload: Input payload (will be JSON serialized)
        invocation_type: "Event" (async) or "RequestResponse" (sync)
        aws_clients: Optional AWSClients instance

    Returns:
        Response payload (only for RequestResponse invocations)

    Raises:
        ClientError: If invocation fails
    """
    if aws_clients is None:
        aws_clients = AWSClients()

    try:
        response = aws_clients.lambda_client.invoke(
            FunctionName=function_name,
            InvocationType=invocation_type,
            Payload=json.dumps(payload)
        )

        logger.info(
            f"Invoked Lambda function: {function_name}",
            extra={
                "function_name": function_name,
                "invocation_type": invocation_type,
                "status_code": response['StatusCode']
            }
        )

        # Parse response for synchronous invocations
        if invocation_type == "RequestResponse":
            response_payload = json.loads(response['Payload'].read())
            return response_payload

        return None

    except ClientError as e:
        logger.error(
            f"Failed to invoke Lambda function: {function_name}",
            extra={
                "function_name": function_name,
                "error": str(e)
            }
        )
        raise


# ============================================================================
# X-Ray Integration (Optional)
# ============================================================================

if ENABLE_XRAY_TRACING:
    try:
        from aws_xray_sdk.core import patch_all
        patch_all()  # Automatically instrument boto3 clients
        logger.info("X-Ray tracing enabled for AWS SDK")
    except ImportError:
        logger.warning("X-Ray SDK not available, tracing disabled")


# ============================================================================
# Global Instance
# ============================================================================

# Pre-initialize clients for Lambda warm starts
aws_clients = AWSClients()
