"""
Structured logging configuration for Zendesk SME Finder.

This module provides JSON-formatted logging with correlation IDs,
CloudWatch integration, and X-Ray tracing support.
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Any, Optional
from functools import wraps

from constants import LOG_LEVEL, ENVIRONMENT, ENABLE_XRAY_TRACING


class StructuredLogger:
    """
    JSON-formatted logger with correlation ID tracking and CloudWatch integration.

    Usage:
        logger = StructuredLogger(__name__)
        logger.info("Ticket processed", extra={"ticket_id": "12345"})
    """

    def __init__(self, name: str, correlation_id: Optional[str] = None):
        """
        Initialize structured logger.

        Args:
            name: Logger name (typically __name__)
            correlation_id: Optional correlation ID for tracing requests
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, LOG_LEVEL))
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.context = {}

        # Configure JSON formatter
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = JSONFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracing."""
        self.correlation_id = correlation_id

    def add_context(self, **kwargs):
        """
        Add persistent context to all log messages.

        Args:
            **kwargs: Key-value pairs to include in all logs
        """
        self.context.update(kwargs)

    def _log(self, level: str, message: str, extra: Optional[dict] = None):
        """
        Internal logging method that enriches log data.

        Args:
            level: Log level (info, warning, error, etc.)
            message: Log message
            extra: Additional structured data
        """
        log_data = {
            "message": message,
            "correlation_id": self.correlation_id,
            "environment": ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **self.context,
            **(extra or {})
        }

        # Add X-Ray trace ID if available
        if ENABLE_XRAY_TRACING:
            try:
                from aws_xray_sdk.core import xray_recorder
                trace_entity = xray_recorder.get_trace_entity()
                if trace_entity:
                    log_data["trace_id"] = trace_entity.trace_id
            except Exception:
                pass  # X-Ray not available, skip

        getattr(self.logger, level)(message, extra=log_data)

    def info(self, message: str, extra: Optional[dict] = None):
        """Log info message with structured data."""
        self._log("info", message, extra)

    def warning(self, message: str, extra: Optional[dict] = None):
        """Log warning message with structured data."""
        self._log("warning", message, extra)

    def error(self, message: str, extra: Optional[dict] = None, exc_info: bool = True):
        """
        Log error message with structured data and exception info.

        Args:
            message: Error message
            extra: Additional structured data
            exc_info: Include exception traceback (default: True)
        """
        self._log("error", message, extra)
        if exc_info:
            self.logger.exception(message)

    def debug(self, message: str, extra: Optional[dict] = None):
        """Log debug message with structured data."""
        self._log("debug", message, extra)

    def critical(self, message: str, extra: Optional[dict] = None):
        """Log critical message with structured data."""
        self._log("critical", message, extra)


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for CloudWatch Logs.

    Outputs logs in JSON format for easy parsing and querying.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def with_logging(func):
    """
    Decorator to automatically log function execution with timing.

    Usage:
        @with_logging
        def my_function(arg1, arg2):
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = StructuredLogger(func.__module__)
        start_time = datetime.utcnow()

        logger.info(
            f"Starting {func.__name__}",
            extra={
                "function": func.__name__,
                "module": func.__module__
            }
        )

        try:
            result = func(*args, **kwargs)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"Completed {func.__name__}",
                extra={
                    "function": func.__name__,
                    "duration_ms": round(duration_ms, 2),
                    "status": "success"
                }
            )

            return result

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.error(
                f"Failed {func.__name__}",
                extra={
                    "function": func.__name__,
                    "duration_ms": round(duration_ms, 2),
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )

            raise

    return wrapper


def log_lambda_event(logger: StructuredLogger, event: dict, context: Any):
    """
    Log Lambda invocation event with context.

    Args:
        logger: StructuredLogger instance
        event: Lambda event dict
        context: Lambda context object
    """
    logger.add_context(
        lambda_request_id=context.request_id,
        lambda_function_name=context.function_name,
        lambda_function_version=context.function_version,
        lambda_memory_limit_mb=context.memory_limit_in_mb
    )

    logger.info(
        "Lambda invocation started",
        extra={
            "event_type": event.get("Records", [{}])[0].get("eventName") if "Records" in event else "unknown",
            "remaining_time_ms": context.get_remaining_time_in_millis()
        }
    )


def log_step_function_input(logger: StructuredLogger, input_data: dict):
    """
    Log Step Functions state input.

    Args:
        logger: StructuredLogger instance
        input_data: Step Functions input dict
    """
    logger.info(
        "Step Functions state started",
        extra={
            "execution_id": input_data.get("execution_id"),
            "state_name": input_data.get("state_name"),
            "input_keys": list(input_data.keys())
        }
    )


# ============================================================================
# CloudWatch Insights Query Examples
# ============================================================================

"""
Example CloudWatch Logs Insights queries:

1. Find all errors for a specific correlation ID:
   fields @timestamp, message, error_type, error_message
   | filter correlation_id = "abc-123"
   | filter level = "ERROR"
   | sort @timestamp desc

2. Average function duration by function name:
   fields function, duration_ms
   | filter status = "success"
   | stats avg(duration_ms) by function

3. Error rate by function:
   fields function
   | stats count() as total, sum(status = "error") as errors by function
   | fields function, errors, total, (errors / total * 100) as error_rate

4. High latency requests (>5 seconds):
   fields @timestamp, function, duration_ms, correlation_id
   | filter duration_ms > 5000
   | sort duration_ms desc

5. Trace all logs for a specific ticket:
   fields @timestamp, message, function
   | filter ticket_id = "12345"
   | sort @timestamp asc
"""
