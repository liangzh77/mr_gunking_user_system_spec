"""JWT token generation and verification service.

This module provides utilities for creating and validating JSON Web Tokens
using the python-jose library with HS256 algorithm.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt

from ..config import get_settings


def create_access_token(
    subject: str,
    user_type: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: Subject identifier (user_id/account_id as string)
        user_type: Type of user ("admin", "operator", "finance")
        expires_delta: Optional custom expiration time delta
        additional_claims: Optional additional claims to include in token

    Returns:
        str: Encoded JWT token

    Example:
        >>> token = create_access_token(
        ...     subject="user123",
        ...     user_type="operator",
        ... )
        >>> len(token) > 0
        True
    """
    settings = get_settings()

    # Calculate expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Build token payload
    to_encode: dict[str, Any] = {
        "sub": subject,
        "user_type": user_type,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    # Add additional claims if provided
    if additional_claims:
        to_encode.update(additional_claims)

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[dict[str, Any]]:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Optional[dict[str, Any]]: Decoded token payload if valid, None otherwise

    Example:
        >>> token = create_access_token("user123", "operator")
        >>> payload = verify_token(token)
        >>> payload is not None
        True
        >>> payload["sub"]
        'user123'
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def decode_token(token: str) -> dict[str, Any]:
    """Decode a JWT token without verification.

    WARNING: This does not verify the token signature!
    Use only for debugging or when signature verification is not needed.

    Args:
        token: JWT token string to decode

    Returns:
        dict[str, Any]: Decoded token payload

    Raises:
        JWTError: If token cannot be decoded

    Example:
        >>> token = create_access_token("user123", "operator")
        >>> payload = decode_token(token)
        >>> payload["user_type"]
        'operator'
    """
    return jwt.decode(token, options={"verify_signature": False})


def is_token_expired(payload: dict[str, Any]) -> bool:
    """Check if a decoded token payload is expired.

    Args:
        payload: Decoded JWT token payload

    Returns:
        bool: True if token is expired, False otherwise

    Example:
        >>> from datetime import timedelta
        >>> # Create expired token
        >>> token = create_access_token(
        ...     "user123", "operator", expires_delta=timedelta(seconds=-1)
        ... )
        >>> payload = decode_token(token)
        >>> is_token_expired(payload)
        True
    """
    exp = payload.get("exp")
    if not exp:
        return True

    # Convert exp to datetime (exp is Unix timestamp)
    exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
    return datetime.now(timezone.utc) >= exp_datetime


def get_token_subject(payload: dict[str, Any]) -> Optional[str]:
    """Extract subject (user_id) from token payload.

    Args:
        payload: Decoded JWT token payload

    Returns:
        Optional[str]: Subject identifier if present, None otherwise

    Example:
        >>> token = create_access_token("user123", "operator")
        >>> payload = verify_token(token)
        >>> get_token_subject(payload)
        'user123'
    """
    return payload.get("sub")


def get_token_user_type(payload: dict[str, Any]) -> Optional[str]:
    """Extract user type from token payload.

    Args:
        payload: Decoded JWT token payload

    Returns:
        Optional[str]: User type if present, None otherwise

    Example:
        >>> token = create_access_token("user123", "operator")
        >>> payload = verify_token(token)
        >>> get_token_user_type(payload)
        'operator'
    """
    return payload.get("user_type")


def refresh_token(token: str, new_expires_delta: Optional[timedelta] = None) -> Optional[str]:
    """Refresh an existing token by creating a new one with updated expiration.

    The new token will have the same claims as the old one, but with a new expiration time.

    Args:
        token: Original JWT token to refresh
        new_expires_delta: Optional custom expiration time delta for new token

    Returns:
        Optional[str]: New JWT token if original is valid, None otherwise

    Example:
        >>> original_token = create_access_token("user123", "operator")
        >>> new_token = refresh_token(original_token)
        >>> new_token is not None
        True
        >>> new_token != original_token
        True
    """
    payload = verify_token(token)
    if not payload:
        return None

    # Extract essential claims
    subject = get_token_subject(payload)
    user_type = get_token_user_type(payload)

    if not subject or not user_type:
        return None

    # Copy additional claims (excluding standard JWT claims)
    standard_claims = {"sub", "user_type", "exp", "iat", "type"}
    additional_claims = {k: v for k, v in payload.items() if k not in standard_claims}

    # Create new token
    return create_access_token(
        subject=subject,
        user_type=user_type,
        expires_delta=new_expires_delta,
        additional_claims=additional_claims if additional_claims else None,
    )
