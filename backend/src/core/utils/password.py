"""Password hashing and verification utilities.

This module provides secure password hashing using bcrypt algorithm
with configurable work factor for computational cost.
"""

from passlib.context import CryptContext

# Bcrypt context with recommended work factor
# rounds=12 provides good security while maintaining reasonable performance
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        password: Plain-text password to hash

    Returns:
        str: Hashed password string (bcrypt format)

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> hashed.startswith("$2b$")
        True
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hashed password.

    Args:
        plain_password: Plain-text password to verify
        hashed_password: Previously hashed password to compare against

    Returns:
        bool: True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    """Check if a password hash needs to be updated.

    This is useful for upgrading password hashes when security
    parameters change (e.g., increasing work factor).

    Args:
        hashed_password: Hashed password to check

    Returns:
        bool: True if hash needs update, False otherwise

    Example:
        >>> hashed = hash_password("password")
        >>> needs_rehash(hashed)
        False
    """
    return pwd_context.needs_update(hashed_password)
