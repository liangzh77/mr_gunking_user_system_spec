"""Bank transfer recharge service

This service handles bank transfer recharge applications submitted by operators.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID as PyUUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import NotFoundException, BadRequestException
from ..models.bank_transfer import BankTransferApplication
from ..models.operator import OperatorAccount
from ..schemas.bank_transfer import (
    BankTransferCreate,
    BankTransferResponse,
    BankTransferListResponse,
)


class BankTransferService:
    """Bank transfer recharge service for operators."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def create_application(
        self,
        operator_id: PyUUID,
        data: BankTransferCreate
    ) -> BankTransferResponse:
        """Create a bank transfer recharge application.

        Args:
            operator_id: Operator ID
            data: Application data

        Returns:
            BankTransferResponse: Created application

        Raises:
            NotFoundException: If operator not found
            BadRequestException: If validation fails
        """
        # Find operator
        result = await self.db.execute(
            select(OperatorAccount).where(OperatorAccount.id == operator_id)
        )
        operator = result.scalar_one_or_none()

        if not operator:
            raise NotFoundException("运营商不存在")

        # Create application record
        application = BankTransferApplication(
            operator_id=operator_id,
            amount=data.amount,
            voucher_image_url=data.voucher_image_url,
            remark=data.remark,
            status="pending"
        )

        self.db.add(application)
        await self.db.commit()
        await self.db.refresh(application)

        # Generate application ID (format: BTR_YYYYMMDD_XXXXX)
        application_created_time = application.created_at
        application_id = f"BTR_{application_created_time.strftime('%Y%m%d')}_{str(application.id)[:5].upper()}"

        # Return response
        return BankTransferResponse(
            id=str(application.id),
            application_id=application_id,
            operator_id=str(application.operator_id),
            amount=str(application.amount),
            voucher_image_url=application.voucher_image_url,
            remark=application.remark,
            status=application.status,
            reject_reason=application.reject_reason,
            reviewed_by=str(application.reviewed_by) if application.reviewed_by else None,
            reviewed_at=application.reviewed_at,
            created_at=application.created_at,
            updated_at=application.updated_at
        )

    async def get_applications(
        self,
        operator_id: PyUUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> BankTransferListResponse:
        """Get bank transfer recharge applications list.

        Args:
            operator_id: Operator ID
            status: Filter by status (pending/approved/rejected/all)
            page: Page number (starts from 1)
            page_size: Items per page

        Returns:
            BankTransferListResponse: Paginated list of applications
        """
        # Build query
        query = select(BankTransferApplication).where(
            BankTransferApplication.operator_id == operator_id
        )

        # Add status filter
        if status and status != "all":
            query = query.where(BankTransferApplication.status == status)

        # Order by created_at desc (newest first)
        query = query.order_by(desc(BankTransferApplication.created_at))

        # Get total count
        count_query = select(func.count()).select_from(BankTransferApplication).where(
            BankTransferApplication.operator_id == operator_id
        )
        if status and status != "all":
            count_query = count_query.where(BankTransferApplication.status == status)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        applications = result.scalars().all()

        # Convert to response items
        items = []
        for app in applications:
            # Generate application ID (format: BTR_YYYYMMDD_XXXXX)
            app_created_time = app.created_at
            application_id = f"BTR_{app_created_time.strftime('%Y%m%d')}_{str(app.id)[:5].upper()}"

            # Convert relative URL to absolute URL
            voucher_url = app.voucher_image_url
            if voucher_url and not voucher_url.startswith(('http://', 'https://', '/')):
                voucher_url = '/' + voucher_url

            items.append(BankTransferResponse(
                id=str(app.id),
                application_id=application_id,
                operator_id=str(app.operator_id),
                amount=str(app.amount),
                voucher_image_url=voucher_url,
                remark=app.remark,
                status=app.status,
                reject_reason=app.reject_reason,
                reviewed_by=str(app.reviewed_by) if app.reviewed_by else None,
                reviewed_at=app.reviewed_at,
                created_at=app.created_at,
                updated_at=app.updated_at
            ))

        return BankTransferListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items
        )

    async def cancel_application(
        self,
        operator_id: PyUUID,
        application_id: PyUUID
    ) -> None:
        """Cancel a pending bank transfer application.

        Args:
            operator_id: Operator ID
            application_id: Application ID

        Raises:
            NotFoundException: If application not found
            BadRequestException: If application already reviewed
        """
        # Find application
        result = await self.db.execute(
            select(BankTransferApplication).where(
                BankTransferApplication.id == application_id,
                BankTransferApplication.operator_id == operator_id
            )
        )
        application = result.scalar_one_or_none()

        if not application:
            raise NotFoundException("申请不存在")

        # Check if already reviewed
        if application.status != "pending":
            raise BadRequestException(f"申请已{self._get_status_label(application.status)},无法取消")

        # Delete application
        await self.db.delete(application)
        await self.db.commit()

    def _get_status_label(self, status: str) -> str:
        """Get status label in Chinese.

        Args:
            status: Status code

        Returns:
            str: Status label
        """
        status_map = {
            "pending": "待审核",
            "approved": "已通过",
            "rejected": "已拒绝"
        }
        return status_map.get(status, status)
