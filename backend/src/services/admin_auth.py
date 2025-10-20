"""Admin authentication service.

This service handles admin login, logout, token management, and user info retrieval.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import (
    UnauthorizedException,
    create_access_token,
    get_cache,
    get_settings,
    get_token_subject,
    hash_password,
    verify_password,
    verify_token,
)
from ..models.admin import AdminAccount
from ..schemas.admin import AdminLoginResponse, AdminUserInfo


class AdminAuthService:
    """Admin authentication service."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db
        self.settings = get_settings()

    async def login(
        self, username: str, password: str, client_ip: str
    ) -> AdminLoginResponse:
        """Authenticate admin and generate access token.

        Args:
            username: Admin username
            password: Plain text password
            client_ip: Client IP address for logging

        Returns:
            AdminLoginResponse: Login response with token and user info

        Raises:
            UnauthorizedException: If credentials are invalid or account is inactive
        """
        # Find admin by username
        result = await self.db.execute(
            select(AdminAccount).where(AdminAccount.username == username)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            raise UnauthorizedException("Invalid username or password")

        # Verify password
        if not verify_password(password, admin.password_hash):
            raise UnauthorizedException("Invalid username or password")

        # Check if account is active
        if not admin.is_active:
            raise UnauthorizedException("Account is inactive")

        # Update last login info
        admin.last_login_at = datetime.now(timezone.utc)
        admin.last_login_ip = client_ip
        await self.db.commit()
        await self.db.refresh(admin)

        # Invalidate cached admin info (if exists) since we updated login time
        cache = get_cache()
        await cache.delete(f"admin:info:{admin.id}")

        # Generate access token
        token = create_access_token(
            subject=str(admin.id),
            user_type="admin",
            additional_claims={
                "username": admin.username,
                "role": admin.role,
            },
        )

        # Calculate token expiration
        expires_in = self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return AdminLoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
            user=AdminUserInfo.model_validate(admin),
        )

    async def get_current_admin(self, token_payload: dict) -> AdminAccount:
        """Get current admin from token payload.

        Args:
            token_payload: Decoded JWT token payload

        Returns:
            AdminAccount: Current admin account

        Raises:
            UnauthorizedException: If admin not found or inactive
        """
        admin_id = get_token_subject(token_payload)
        if not admin_id:
            raise UnauthorizedException("Invalid token")

        # Try to get from cache first
        cache = get_cache()
        cache_key = f"admin:info:{admin_id}"
        cached_admin = await cache.get(cache_key)

        if cached_admin:
            # Reconstruct AdminAccount from cached data
            # Convert serialized fields back to their proper types
            if cached_admin.get("id"):
                cached_admin["id"] = UUID(cached_admin["id"])
            if cached_admin.get("created_at"):
                cached_admin["created_at"] = datetime.fromisoformat(cached_admin["created_at"])
            if cached_admin.get("updated_at"):
                cached_admin["updated_at"] = datetime.fromisoformat(cached_admin["updated_at"])
            if cached_admin.get("last_login_at"):
                cached_admin["last_login_at"] = datetime.fromisoformat(cached_admin["last_login_at"])
            if cached_admin.get("created_by"):
                cached_admin["created_by"] = UUID(cached_admin["created_by"])

            admin = AdminAccount(**cached_admin)
            if not admin.is_active:
                raise UnauthorizedException("Account is inactive")
            return admin

        # Cache miss - query database
        result = await self.db.execute(
            select(AdminAccount).where(AdminAccount.id == admin_id)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            raise UnauthorizedException("Admin not found")

        if not admin.is_active:
            raise UnauthorizedException("Account is inactive")

        # Cache admin info for 10 minutes
        admin_dict = {
            "id": str(admin.id),
            "username": admin.username,
            "full_name": admin.full_name,
            "email": admin.email,
            "phone": admin.phone,
            "role": admin.role,
            "permissions": admin.permissions,
            "is_active": admin.is_active,
            "password_hash": admin.password_hash,
            "created_at": admin.created_at.isoformat() if admin.created_at else None,
            "updated_at": admin.updated_at.isoformat() if admin.updated_at else None,
            "last_login_at": admin.last_login_at.isoformat() if admin.last_login_at else None,
            "last_login_ip": admin.last_login_ip,
            "created_by": str(admin.created_by) if admin.created_by else None,
        }
        await cache.set(cache_key, admin_dict, ttl=600)

        return admin

    async def get_user_info(self, admin_id: str) -> AdminUserInfo:
        """Get admin user information.

        Args:
            admin_id: Admin account ID

        Returns:
            AdminUserInfo: Admin user information

        Raises:
            UnauthorizedException: If admin not found
        """
        result = await self.db.execute(
            select(AdminAccount).where(AdminAccount.id == admin_id)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            raise UnauthorizedException("Admin not found")

        return AdminUserInfo.model_validate(admin)

    async def refresh_token(self, old_token: str) -> AdminLoginResponse:
        """Refresh access token.

        Args:
            old_token: Current access token

        Returns:
            AdminLoginResponse: New token and user info

        Raises:
            UnauthorizedException: If token is invalid
        """
        payload = verify_token(old_token)
        if not payload:
            raise UnauthorizedException("Invalid token")

        admin_id = get_token_subject(payload)
        if not admin_id:
            raise UnauthorizedException("Invalid token")

        # Get admin
        result = await self.db.execute(
            select(AdminAccount).where(AdminAccount.id == admin_id)
        )
        admin = result.scalar_one_or_none()

        if not admin or not admin.is_active:
            raise UnauthorizedException("Admin not found or inactive")

        # Generate new token
        new_token = create_access_token(
            subject=str(admin.id),
            user_type="admin",
            additional_claims={
                "username": admin.username,
                "role": admin.role,
            },
        )

        expires_in = self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return AdminLoginResponse(
            access_token=new_token,
            token_type="bearer",
            expires_in=expires_in,
            user=AdminUserInfo.model_validate(admin),
        )

    async def change_password(
        self, admin_id: str, old_password: str, new_password: str
    ) -> bool:
        """Change admin password.

        Args:
            admin_id: Admin account ID
            old_password: Current password
            new_password: New password

        Returns:
            bool: True if password changed successfully

        Raises:
            UnauthorizedException: If old password is incorrect
        """
        result = await self.db.execute(
            select(AdminAccount).where(AdminAccount.id == admin_id)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            raise UnauthorizedException("Admin not found")

        # Verify old password
        if not verify_password(old_password, admin.password_hash):
            raise UnauthorizedException("Current password is incorrect")

        # Update password
        admin.password_hash = hash_password(new_password)
        admin.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        # Invalidate cached admin info since password changed
        cache = get_cache()
        await cache.delete(f"admin:info:{admin_id}")

        return True
