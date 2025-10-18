"""Finance authentication and authorization service (T168).

This service handles finance staff login and permission management.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID as PyUUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import UnauthorizedException, BadRequestException
from ..core.utils.password import verify_password
from ..models.finance import FinanceAccount
from ..schemas.finance import FinanceLoginResponse, FinanceInfo


class FinanceService:
    """Finance authentication and authorization service."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def login(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> FinanceLoginResponse:
        """Finance staff login.

        Args:
            username: Finance staff username
            password: Password
            ip_address: Client IP address (for login tracking)

        Returns:
            FinanceLoginResponse: Login response with JWT token

        Raises:
            UnauthorizedException: If credentials are invalid or account is inactive
        """
        # Find finance account by username
        result = await self.db.execute(
            select(FinanceAccount).where(FinanceAccount.username == username)
        )
        finance = result.scalar_one_or_none()

        # Check if account exists
        if not finance:
            raise UnauthorizedException("用户名或密码错误")

        # Verify password
        if not verify_password(password, finance.password_hash):
            raise UnauthorizedException("用户名或密码错误")

        # Check if account is active
        if not finance.is_active:
            raise UnauthorizedException("账号已禁用，请联系管理员")

        # Update last login info
        finance.last_login_at = datetime.now(timezone.utc)
        if ip_address:
            finance.last_login_ip = ip_address

        await self.db.commit()
        await self.db.refresh(finance)

        # Generate JWT token (placeholder - should use actual JWT service)
        from ..core.utils.jwt import create_access_token

        # Token payload
        token_data = {
            "sub": str(finance.id),
            "username": finance.username,
            "role": finance.role,
            "type": "finance"
        }

        # Create access token (expires in 24 hours)
        access_token = create_access_token(token_data, expires_delta=timedelta(hours=24))

        # Build response
        return FinanceLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=86400,  # 24 hours in seconds
            finance=FinanceInfo(
                finance_id=str(finance.id),
                username=finance.username,
                full_name=finance.full_name,
                role=finance.role,
                email=finance.email
            )
        )

    async def get_finance_by_id(self, finance_id: PyUUID) -> Optional[FinanceAccount]:
        """Get finance account by ID.

        Args:
            finance_id: Finance account ID

        Returns:
            Optional[FinanceAccount]: Finance account or None if not found
        """
        result = await self.db.execute(
            select(FinanceAccount).where(FinanceAccount.id == finance_id)
        )
        return result.scalar_one_or_none()

    async def check_permission(
        self,
        finance_id: PyUUID,
        required_permission: str
    ) -> bool:
        """Check if finance staff has a specific permission.

        Args:
            finance_id: Finance account ID
            required_permission: Permission to check (e.g., "refund_review", "invoice_review")

        Returns:
            bool: True if has permission, False otherwise
        """
        finance = await self.get_finance_by_id(finance_id)

        if not finance or not finance.is_active:
            return False

        # Check role-based permissions
        # Manager and auditor have all permissions
        if finance.role in ["manager", "auditor"]:
            return True

        # Specialist has limited permissions based on permissions JSONB field
        if finance.role == "specialist":
            # Check permissions field
            permissions = finance.permissions or {}
            return permissions.get(required_permission, False)

        return False

    async def verify_active_finance(self, finance_id: PyUUID) -> FinanceAccount:
        """Verify that finance account exists and is active.

        Args:
            finance_id: Finance account ID

        Returns:
            FinanceAccount: Active finance account

        Raises:
            UnauthorizedException: If account not found or inactive
        """
        finance = await self.get_finance_by_id(finance_id)

        if not finance:
            raise UnauthorizedException("财务账号不存在")

        if not finance.is_active:
            raise UnauthorizedException("财务账号已禁用")

        return finance
