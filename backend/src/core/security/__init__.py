"""Security module containing authentication and authorization utilities."""

from typing import Optional

from .jwt import (
    create_access_token,
    create_headset_token,
    decode_token,
    get_token_subject,
    get_token_user_type,
    is_token_expired,
    refresh_token,
    verify_token,
)
from .encryption import EncryptionService, EncryptionError

# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get global encryption service instance.

    Returns:
        EncryptionService: Singleton encryption service
    """
    global _encryption_service

    if _encryption_service is None:
        from ..config import get_settings
        settings = get_settings()
        _encryption_service = EncryptionService(
            master_key=settings.ENCRYPTION_KEY,
            key_version="v1"
        )

    return _encryption_service


__all__ = [
    "create_access_token",
    "create_headset_token",
    "verify_token",
    "decode_token",
    "is_token_expired",
    "get_token_subject",
    "get_token_user_type",
    "refresh_token",
    "EncryptionService",
    "EncryptionError",
    "get_encryption_service",
]
