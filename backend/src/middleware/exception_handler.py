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

        # If detail is a dict (custom error response like {error_code, message}), return it directly
        # This is used by our service layer exceptions
        if isinstance(exc.detail, dict):
            content = exc.detail
        else:
            # For string messages, wrap in standard format
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
            JSONResponse: Validation error response (400 Bad Request with error_code/message)
        """
        logger.warning(
            "validation_error",
            path=request.url.path,
            method=request.method,
            errors=exc.errors(),
        )

        # 提取第一个验证错误信息
        errors = exc.errors()
        first_error = errors[0] if errors else {}
        field = first_error.get("loc", [])[-1] if first_error.get("loc") else "unknown"
        error_type = first_error.get("type", "validation_error")

        # 构造友好的错误消息
        if "missing" in error_type:
            message = f"缺少必填字段: {field}"
        elif "string_too_short" in error_type:
            message = f"字段 {field} 长度不足"
        elif "string_too_long" in error_type:
            message = f"字段 {field} 长度超限"
        elif "value_error" in error_type:
            # 对于field_validator抛出的ValueError,从msg中提取友好消息
            msg = first_error.get("msg", "")
            if "Value error, " in msg:
                message = msg.replace("Value error, ", "")
            else:
                message = msg
        else:
            message = first_error.get("msg", "请求参数验证失败")

        # 序列化errors,移除不可序列化的对象(如ValueError实例)
        serializable_errors = []
        for error in errors:
            serializable_error = {
                "type": error.get("type"),
                "loc": error.get("loc"),
                "msg": error.get("msg"),
                "input": str(error.get("input")) if error.get("input") is not None else None,
            }
            # ctx中可能包含不可序列化的对象,只保留字符串表示
            if "ctx" in error and error["ctx"]:
                serializable_error["ctx"] = {
                    k: str(v) for k, v in error["ctx"].items()
                }
            serializable_errors.append(serializable_error)

        # 返回契约格式(error_code + message)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,  # 改为400而非422
            content={
                "error_code": "INVALID_PARAMS",
                "message": message,
                "details": serializable_errors,  # 保留详细错误信息用于调试(已序列化)
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
