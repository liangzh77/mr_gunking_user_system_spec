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
from ..schemas.finance.bank_transfer import (
    BankTransferListRequest,
    BankTransferListResponse as FinanceBankTransferListResponse,
    BankTransferItem,
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

        # Return response
        return BankTransferResponse(
            id=str(application.id),
            application_id=str(application.id),
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
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> BankTransferListResponse:
        """Get bank transfer recharge applications list.

        Args:
            operator_id: Operator ID
            status: Filter by status (pending/approved/rejected/all)
            search: Search by application ID, remark, reject reason
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

        # Add search filter
        if search:
            from sqlalchemy import cast, String, or_
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    cast(BankTransferApplication.id, String).ilike(search_pattern),
                    BankTransferApplication.remark.ilike(search_pattern),
                    BankTransferApplication.reject_reason.ilike(search_pattern)
                )
            )

        # Order by created_at desc (newest first)
        query = query.order_by(desc(BankTransferApplication.created_at))

        # Get total count
        count_query = select(func.count()).select_from(BankTransferApplication).where(
            BankTransferApplication.operator_id == operator_id
        )
        if status and status != "all":
            count_query = count_query.where(BankTransferApplication.status == status)
        if search:
            from sqlalchemy import cast, String, or_
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                or_(
                    cast(BankTransferApplication.id, String).ilike(search_pattern),
                    BankTransferApplication.remark.ilike(search_pattern),
                    BankTransferApplication.reject_reason.ilike(search_pattern)
                )
            )

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
            # Convert relative URL to absolute URL
            voucher_url = app.voucher_image_url
            if voucher_url and not voucher_url.startswith(('http://', 'https://', '/')):
                voucher_url = '/' + voucher_url

            items.append(BankTransferResponse(
                id=str(app.id),
                application_id=str(app.id),
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

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return BankTransferListResponse(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
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

    async def get_applications_for_finance(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        operator_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> FinanceBankTransferListResponse:
        """Get bank transfer applications for finance review.

        Args:
            status: Filter by status
            search: Search keyword
            operator_id: Filter by operator ID
            page: Page number
            page_size: Page size
            start_date: Start date filter
            end_date: End date filter

        Returns:
            FinanceBankTransferListResponse: Paginated applications
        """
        # Build query
        query = (
            select(
                BankTransferApplication,
                OperatorAccount.username,
                OperatorAccount.full_name
            )
            .join(OperatorAccount, BankTransferApplication.operator_id == OperatorAccount.id)
        )

        # Apply filters
        if status:
            query = query.where(BankTransferApplication.status == status)

        if operator_id:
            # Handle op_ prefix format
            actual_operator_id = operator_id.replace("op_", "") if operator_id.startswith("op_") else operator_id
            try:
                operator_uuid = PyUUID(actual_operator_id)
                query = query.where(BankTransferApplication.operator_id == operator_uuid)
            except ValueError:
                # Invalid UUID, return empty result
                return FinanceBankTransferListResponse(
                    items=[],
                    total=0,
                    page=page,
                    page_size=page_size,
                    total_pages=0
                )

        if search:
            from sqlalchemy import cast, String, or_
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    OperatorAccount.username.ilike(search_pattern),
                    OperatorAccount.full_name.ilike(search_pattern),
                    cast(BankTransferApplication.id, String).ilike(search_pattern),
                    BankTransferApplication.remark.ilike(search_pattern),
                    BankTransferApplication.reject_reason.ilike(search_pattern)
                )
            )

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.where(BankTransferApplication.created_at >= start_dt)
            except ValueError:
                pass  # Invalid date format, ignore filter

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                # Add one day to make it inclusive
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.where(BankTransferApplication.created_at <= end_dt)
            except ValueError:
                pass  # Invalid date format, ignore filter

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(desc(BankTransferApplication.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        rows = result.all()

        # Convert to response items
        items = []
        for row in rows:
            application = row.BankTransferApplication
            operator_username = row.username
            operator_full_name = row.full_name

            items.append(BankTransferItem(
                id=str(application.id),
                application_id=str(application.id),
                operator_id=str(application.operator_id),
                operator_name=operator_full_name,
                operator_username=operator_username,
                amount=float(application.amount),
                voucher_image_url=application.voucher_image_url,
                remark=application.remark,
                status=application.status,
                reject_reason=application.reject_reason,
                created_at=application.created_at,
                reviewed_at=application.reviewed_at,
                reviewed_by=str(application.reviewed_by) if application.reviewed_by else None
            ))

        total_pages = (total + page_size - 1) // page_size

        return FinanceBankTransferListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    async def approve_application(
        self,
        transfer_uuid: PyUUID,
        reviewer_id: PyUUID
    ) -> BankTransferApplication:
        """Approve a bank transfer application.

        Args:
            transfer_uuid: Application UUID
            reviewer_id: Reviewer UUID

        Returns:
            BankTransferApplication: Updated application

        Raises:
            NotFoundException: If application not found
            BadRequestException: If application not in pending status
        """
        from ..models.transaction import TransactionRecord, TransactionType
        from sqlalchemy import select as sql_select

        # Get application
        result = await self.db.execute(
            select(BankTransferApplication).where(
                BankTransferApplication.id == transfer_uuid
            )
        )
        application = result.scalar_one_or_none()

        if not application:
            raise NotFoundException("银行转账申请不存在")

        if application.status != "pending":
            raise BadRequestException(f"申请状态为{self._get_status_label(application.status)}，无法批准")

        # Get operator account with row-level lock to ensure balance consistency
        operator_result = await self.db.execute(
            sql_select(OperatorAccount)
            .where(OperatorAccount.id == application.operator_id)
            .with_for_update()
        )
        operator = operator_result.scalar_one_or_none()

        if not operator:
            raise NotFoundException("运营商账户不存在")

        # Calculate balance changes
        balance_before = operator.balance
        balance_after = balance_before + application.amount

        # Create recharge transaction record
        transaction = TransactionRecord(
            operator_id=application.operator_id,
            transaction_type=TransactionType.RECHARGE.value,
            amount=application.amount,
            balance_before=balance_before,
            balance_after=balance_after,
            payment_channel="bank_transfer",
            payment_status="success",
            payment_callback_at=datetime.now(timezone.utc),
            description=f"银行转账充值 - 申请ID: {application.id}"
        )
        self.db.add(transaction)

        # Update operator balance
        operator.balance = balance_after

        # Update application status
        application.status = "approved"
        application.reviewed_at = datetime.now(timezone.utc)
        application.reviewed_by = reviewer_id

        await self.db.commit()
        await self.db.refresh(application)

        return application

    async def reject_application(
        self,
        transfer_uuid: PyUUID,
        reviewer_id: PyUUID,
        reject_reason: str
    ) -> BankTransferApplication:
        """Reject a bank transfer application.

        Args:
            transfer_uuid: Application UUID
            reviewer_id: Reviewer UUID
            reject_reason: Rejection reason

        Returns:
            BankTransferApplication: Updated application

        Raises:
            NotFoundException: If application not found
            BadRequestException: If application not in pending status
        """
        # Get application
        result = await self.db.execute(
            select(BankTransferApplication).where(
                BankTransferApplication.id == transfer_uuid
            )
        )
        application = result.scalar_one_or_none()

        if not application:
            raise NotFoundException("银行转账申请不存在")

        if application.status != "pending":
            raise BadRequestException(f"申请状态为{self._get_status_label(application.status)}，无法拒绝")

        # Update application status
        application.status = "rejected"
        application.reject_reason = reject_reason
        application.reviewed_at = datetime.now(timezone.utc)
        application.reviewed_by = reviewer_id

        await self.db.commit()
        await self.db.refresh(application)

        return application

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
            "rejected": "已拒绝",
            "cancelled": "已取消"
        }
        return status_map.get(status, status)
