"""Dependency injection factories for FastAPI endpoints.

This module provides reusable dependencies for authentication,
authorization, and common parameter extraction.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import verify_token
from ..db import get_db_session


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
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Extract and verify JWT token from Authorization header.

    Args:
        authorization: Authorization header value

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
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "MISSING_TOKEN",
                "message": "Missing authorization header"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN_FORMAT",
                "message": "Invalid authorization header format"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

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


# Type annotations for user types
AdminUser = Annotated[dict, Depends(require_admin)]
OperatorUser = Annotated[dict, Depends(require_operator)]
FinanceUser = Annotated[dict, Depends(require_finance)]
