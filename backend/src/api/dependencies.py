"""Dependency injection factories for FastAPI endpoints.

This module provides reusable dependencies for authentication,
authorization, and common parameter extraction.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import verify_token
from ..db import get_db_session

# HTTP Bearer security scheme for Swagger UI
http_bearer = HTTPBearer(auto_error=False)


# Database session dependency
async def get_db() -> AsyncSession:
    """Get database session dependency (alias for get_db_session).

    This is a convenience alias for use in FastAPI endpoints.

    Yields:
        AsyncSession: Database session

    Example:
        >>> @app.get("/users")
        ... async def get_users(db: AsyncSession = Depends(get_db)):
        ...     ...
    """
    async for session in get_db_session():
        yield session


# Database session type annotation
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


# JWT Authentication dependency
async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> dict:
    """Extract and verify JWT token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials from Authorization header

    Returns:
        dict: Decoded JWT token payload

    Raises:
        HTTPException: If token is missing, invalid, or expired

    Example:
        >>> @app.get("/protected")
        ... async def protected_route(token: dict = Depends(get_current_user_token)):
        ...     user_id = token["sub"]
        ...     ...
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "MISSING_TOKEN",
                "message": "Missing authorization header"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from credentials
    token = credentials.credentials

    # Verify token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Invalid or expired token"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


# Current user token type annotation
CurrentUserToken = Annotated[dict, Depends(get_current_user_token)]


# User type-specific dependencies
async def require_admin(token: CurrentUserToken) -> dict:
    """Require admin user type.

    Args:
        token: Current user token payload

    Returns:
        dict: Token payload

    Raises:
        HTTPException: If user is not admin

    Example:
        >>> @app.get("/admin")
        ... async def admin_only(token: dict = Depends(require_admin)):
        ...     ...
    """
    if token.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return token


async def require_operator(token: CurrentUserToken) -> dict:
    """Require operator user type.

    Args:
        token: Current user token payload

    Returns:
        dict: Token payload

    Raises:
        HTTPException: If user is not operator
    """
    if token.get("user_type") != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator access required",
        )
    return token


async def require_finance(token: CurrentUserToken) -> dict:
    """Require finance user type.

    Args:
        token: Current user token payload

    Returns:
        dict: Token payload

    Raises:
        HTTPException: If user is not finance
    """
    if token.get("user_type") != "finance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Finance access required",
        )
    return token


async def require_headset_token(token: CurrentUserToken) -> dict:
    """Require headset token (for headset server APIs only).

    This dependency ensures that only headset tokens (not regular operator
    login tokens) can access headset server APIs like game authorization.

    Args:
        token: Current token payload

    Returns:
        dict: Token payload

    Raises:
        HTTPException: If token is not a headset token or not for an operator

    Example:
        >>> @app.post("/game/authorize")
        ... async def authorize(token: dict = Depends(require_headset_token)):
        ...     # Only headset tokens can reach here
        ...     ...
    """
    # Must be a headset type token
    if token.get("type") != "headset":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "INVALID_TOKEN_TYPE",
                "message": "This endpoint requires a headset token. Please use the token provided when launching the application."
            },
        )

    # Must be for an operator account
    if token.get("user_type") != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "INVALID_USER_TYPE",
                "message": "Headset token must be associated with an operator account"
            },
        )

    return token


# Type annotations for user types
AdminUser = Annotated[dict, Depends(require_admin)]
OperatorUser = Annotated[dict, Depends(require_operator)]
FinanceUser = Annotated[dict, Depends(require_finance)]
HeadsetToken = Annotated[dict, Depends(require_headset_token)]
