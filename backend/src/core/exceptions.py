"""Custom exception classes for the application.

This module defines custom exceptions with HTTP status codes
for consistent error handling across the application.
"""

from typing import Any


class AppException(Exception):
    """Base exception for all application exceptions.

    Attributes:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        """Initialize AppException.

        Args:
            message: Error message
            status_code: HTTP status code (default: 500)
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class BadRequestException(AppException):
    """400 Bad Request exception."""

    def __init__(self, message: str = "Bad request", details: dict[str, Any] | None = None):
        super().__init__(message, status_code=400, details=details)


class UnauthorizedException(AppException):
    """401 Unauthorized exception."""

    def __init__(
        self, message: str = "Unauthorized", details: dict[str, Any] | None = None
    ):
        super().__init__(message, status_code=401, details=details)


class ForbiddenException(AppException):
    """403 Forbidden exception."""

    def __init__(self, message: str = "Forbidden", details: dict[str, Any] | None = None):
        super().__init__(message, status_code=403, details=details)


class NotFoundException(AppException):
    """404 Not Found exception."""

    def __init__(
        self, message: str = "Resource not found", details: dict[str, Any] | None = None
    ):
        super().__init__(message, status_code=404, details=details)


class ConflictException(AppException):
    """409 Conflict exception."""

    def __init__(self, message: str = "Conflict", details: dict[str, Any] | None = None):
        super().__init__(message, status_code=409, details=details)


class UnprocessableEntityException(AppException):
    """422 Unprocessable Entity exception."""

    def __init__(
        self,
        message: str = "Unprocessable entity",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=422, details=details)


class InternalServerException(AppException):
    """500 Internal Server Error exception."""

    def __init__(
        self,
        message: str = "Internal server error",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=500, details=details)


class ServiceUnavailableException(AppException):
    """503 Service Unavailable exception."""

    def __init__(
        self,
        message: str = "Service unavailable",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=503, details=details)
