"""
Bedrock API error handling with throttling and retry logic.

This module provides production-grade error handling for AWS Bedrock API calls,
including throttling detection, exponential backoff, and circuit breaker pattern.
"""

import time
from functools import wraps
from typing import Callable, Any
from enum import Enum
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

from logging_config import StructuredLogger
from constants import (
    BEDROCK_MAX_RETRIES,
    BEDROCK_BACKOFF_MULTIPLIER,
    BEDROCK_BACKOFF_MAX
)

logger = StructuredLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pattern for cascading failure prevention.

    Automatically opens circuit after threshold failures, preventing
    further requests until timeout period expires.
    """

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before attempting half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def record_success(self):
        """Record successful operation, reset failure count."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.debug("Circuit breaker: Success recorded, circuit closed")

    def record_failure(self):
        """Record failed operation, potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker: Opened after {self.failure_count} failures",
                extra={"failure_count": self.failure_count}
            )

    def can_execute(self) -> bool:
        """
        Check if operation can be executed based on circuit state.

        Returns:
            True if operation can proceed, False otherwise
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).seconds
                if elapsed > self.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker: Entering half-open state")
                    return True

            logger.warning("Circuit breaker: Open, rejecting request")
            return False

        return self.state == CircuitState.HALF_OPEN


# Global circuit breaker instance for Bedrock API
bedrock_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)


def handle_bedrock_throttling(func: Callable) -> Callable:
    """
    Decorator to handle Bedrock API throttling with exponential backoff.

    Handles:
    - ThrottlingException
    - ServiceUnavailableException
    - ModelTimeoutException
    - Circuit breaker pattern

    Args:
        func: Function to wrap with error handling

    Returns:
        Wrapped function with retry logic
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        base_wait_time = 1

        for attempt in range(BEDROCK_MAX_RETRIES):
            # Check circuit breaker
            if not bedrock_circuit_breaker.can_execute():
                raise Exception("Circuit breaker open, Bedrock API unavailable")

            try:
                result = func(*args, **kwargs)
                bedrock_circuit_breaker.record_success()
                return result

            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']

                # Log error details
                logger.warning(
                    f"Bedrock API error: {error_code}",
                    extra={
                        "error_code": error_code,
                        "error_message": error_message,
                        "attempt": attempt + 1,
                        "max_retries": BEDROCK_MAX_RETRIES
                    }
                )

                # Handle throttling and retryable errors
                if error_code in [
                    'ThrottlingException',
                    'ServiceUnavailableException',
                    'ModelTimeoutException',
                    'TooManyRequestsException'
                ]:
                    if attempt == BEDROCK_MAX_RETRIES - 1:
                        bedrock_circuit_breaker.record_failure()
                        logger.error(
                            f"Max retries exceeded for Bedrock API",
                            extra={"error_code": error_code}
                        )
                        raise

                    # Calculate wait time with exponential backoff
                    wait_time = min(
                        base_wait_time * (BEDROCK_BACKOFF_MULTIPLIER ** attempt),
                        BEDROCK_BACKOFF_MAX
                    )

                    logger.info(
                        f"Bedrock throttled, retrying in {wait_time}s",
                        extra={
                            "attempt": attempt + 1,
                            "wait_time": wait_time,
                            "error_code": error_code
                        }
                    )

                    time.sleep(wait_time)
                    continue

                # Non-retryable errors
                elif error_code in [
                    'ValidationException',
                    'AccessDeniedException',
                    'ResourceNotFoundException'
                ]:
                    logger.error(
                        f"Non-retryable Bedrock error: {error_code}",
                        extra={
                            "error_code": error_code,
                            "error_message": error_message
                        }
                    )
                    raise

                # Unknown error, don't retry
                else:
                    logger.error(
                        f"Unknown Bedrock error: {error_code}",
                        extra={
                            "error_code": error_code,
                            "error_message": error_message
                        }
                    )
                    raise

            except Exception as e:
                # Non-ClientError exceptions
                logger.error(
                    f"Unexpected error in Bedrock API call: {str(e)}",
                    extra={
                        "error_type": type(e).__name__,
                        "attempt": attempt + 1
                    }
                )

                if attempt == BEDROCK_MAX_RETRIES - 1:
                    bedrock_circuit_breaker.record_failure()
                    raise

                wait_time = min(
                    base_wait_time * (BEDROCK_BACKOFF_MULTIPLIER ** attempt),
                    BEDROCK_BACKOFF_MAX
                )
                time.sleep(wait_time)

        # Should not reach here, but handle gracefully
        raise Exception(f"Max retries ({BEDROCK_MAX_RETRIES}) exceeded")

    return wrapper


def validate_bedrock_response(response: dict) -> dict:
    """
    Validate Bedrock API response structure.

    Args:
        response: Raw response from Bedrock API

    Returns:
        Validated response dict

    Raises:
        ValueError: If response is invalid
    """
    if not response:
        raise ValueError("Empty response from Bedrock API")

    if 'body' not in response:
        raise ValueError("Missing 'body' in Bedrock response")

    return response


def calculate_bedrock_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int = 0
) -> float:
    """
    Calculate estimated cost for Bedrock API call.

    Args:
        model_id: Bedrock model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens (0 for embeddings)

    Returns:
        Estimated cost in USD
    """
    # Pricing as of 2025 (per 1M tokens)
    CLAUDE_SONNET_4_5_PRICING = {
        "input_per_1m": 3.00,
        "output_per_1m": 15.00
    }

    TITAN_EMBEDDINGS_PRICING = {
        "input_per_1m": 0.02
    }

    if "claude-sonnet" in model_id.lower():
        input_cost = (input_tokens / 1_000_000) * CLAUDE_SONNET_4_5_PRICING["input_per_1m"]
        output_cost = (output_tokens / 1_000_000) * CLAUDE_SONNET_4_5_PRICING["output_per_1m"]
        return round(input_cost + output_cost, 6)

    elif "titan-embed" in model_id.lower():
        return round((input_tokens / 1_000_000) * TITAN_EMBEDDINGS_PRICING["input_per_1m"], 6)

    logger.warning(f"Unknown model ID for cost calculation: {model_id}")
    return 0.0


def extract_token_usage(response: dict, model_id: str) -> dict:
    """
    Extract token usage from Bedrock response.

    Args:
        response: Bedrock API response
        model_id: Model identifier

    Returns:
        Dict with input_tokens, output_tokens, total_tokens
    """
    try:
        if "claude" in model_id.lower():
            # Claude models return usage in response
            usage = response.get("usage", {})
            return {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            }
        elif "titan-embed" in model_id.lower():
            # Titan embeddings only have input tokens
            return {
                "input_tokens": response.get("inputTextTokenCount", 0),
                "output_tokens": 0,
                "total_tokens": response.get("inputTextTokenCount", 0)
            }
    except Exception as e:
        logger.warning(f"Failed to extract token usage: {str(e)}")

    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
