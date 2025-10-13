"""Global exception handlers for FastAPI.

This module provides exception handlers for custom exceptions
and standard HTTP exceptions.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..core.exceptions import AppException
from ..core.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """Handle custom application exceptions.

        Args:
            request: FastAPI request object
            exc: Application exception

        Returns:
            JSONResponse: Error response with details
        """
        logger.error(
            "app_exception",
            path=request.url.path,
            method=request.method,
            status_code=exc.status_code,
            message=exc.message,
            details=exc.details,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    **exc.details,
                },
                "message": exc.message,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle standard HTTP exceptions.

        Args:
            request: FastAPI request object
            exc: HTTP exception

        Returns:
            JSONResponse: Error response
        """
        logger.warning(
            "http_exception",
            path=request.url.path,
            method=request.method,
            status_code=exc.status_code,
            detail=exc.detail,
        )

        # If detail is a dict (custom error response), keep it in 'detail' field
        # Otherwise, wrap string message in standard format
        if isinstance(exc.detail, dict):
            content = {"detail": exc.detail}
        else:
            content = {
                "success": False,
                "error": {
                    "type": "HTTPException",
                    "message": exc.detail,
                },
                "message": exc.detail,
            }

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors (Pydantic).

        Args:
            request: FastAPI request object
            exc: Validation error

        Returns:
            JSONResponse: Validation error response
        """
        logger.warning(
            "validation_error",
            path=request.url.path,
            method=request.method,
            errors=exc.errors(),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "type": "ValidationError",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                },
                "message": "Request validation failed",
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions.

        Args:
            request: FastAPI request object
            exc: Unexpected exception

        Returns:
            JSONResponse: Generic error response
        """
        logger.error(
            "unexpected_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "type": "InternalServerError",
                    "message": "An unexpected error occurred",
                },
                "message": "An unexpected error occurred",
            },
        )
