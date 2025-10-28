"""Structured logging configuration using structlog.

This module provides structured logging with both JSON and text output formats,
context binding, and integration with standard library logging.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from .config import get_settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log events.

    Args:
        logger: Logger instance
        method_name: Name of the logging method called
        event_dict: Event dictionary to modify

    Returns:
        EventDict: Modified event dictionary with app context
    """
    settings = get_settings()
    event_dict["app_name"] = settings.APP_NAME
    event_dict["app_version"] = settings.APP_VERSION
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def drop_debug_logs_in_production(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Drop DEBUG level logs in production environment.

    Args:
        logger: Logger instance
        method_name: Name of the logging method called
        event_dict: Event dictionary

    Returns:
        EventDict: Event dictionary (unchanged)

    Raises:
        structlog.DropEvent: If DEBUG log in production
    """
    settings = get_settings()
    if settings.is_production and event_dict.get("level") == "debug":
        raise structlog.DropEvent
    return event_dict


def configure_logging() -> None:
    """Configure structured logging for the application.

    This function sets up:
    - Structlog with JSON or text output based on configuration
    - Standard library logging integration
    - Log level configuration
    - Processors for adding context and formatting

    Should be called once at application startup.
    """
    settings = get_settings()

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )

    # Define processors based on output format
    processors: list[Processor] = [
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add application context
        add_app_context,
        # Drop debug logs in production
        drop_debug_logs_in_production,
        # Stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.format_exc_info,
        # Decode unicode
        structlog.processors.UnicodeDecoder(),
    ]

    # Add format-specific processors
    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        structlog.stdlib.BoundLogger: Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_login", user_id="123", ip="127.0.0.1")
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to the current thread's logger.

    Context variables will be automatically included in all log messages
    within the current thread/request.

    Args:
        **kwargs: Key-value pairs to bind to logger context

    Example:
        >>> bind_context(request_id="abc-123", user_id="456")
        >>> logger = get_logger(__name__)
        >>> logger.info("operation_completed")  # Will include request_id and user_id
    """
    structlog.threadlocal.bind_threadlocal(**kwargs)


def unbind_context(*keys: str) -> None:
    """Unbind specific context variables from the current thread's logger.

    Args:
        *keys: Keys to remove from logger context

    Example:
        >>> unbind_context("request_id", "user_id")
    """
    structlog.threadlocal.unbind_threadlocal(*keys)


def clear_context() -> None:
    """Clear all context variables from the current thread's logger.

    Example:
        >>> clear_context()
    """
    structlog.threadlocal.clear_threadlocal()
