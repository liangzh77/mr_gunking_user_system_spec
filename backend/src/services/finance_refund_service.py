"""Finance refund review service (T170).

This service handles refund application review operations by finance staff.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID as PyUUID

from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import NotFoundException, BadRequestException
from ..models.refund import RefundRecord
from ..models.operator import OperatorAccount
from ..models.transaction import TransactionRecord
from ..schemas.finance import (
    RefundItemFinance,
    RefundListResponse,
    RefundDetailsResponse,
    RefundApproveResponse,
    CustomerFinanceDetails
)
from .audit_log_service import AuditLogService
from .message_service import MessageService


class FinanceRefundService:
    """Finance refund review service."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_refunds(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> RefundListResponse:
        """Get refund applications list.

        Args:
            status: Filter by status (pending/approved/rejected/all)
            search: Search by operator name or refund ID
            page: Page number (starts from 1)
            page_size: Items per page

        Returns:
            RefundListResponse: Paginated list of refund applications
        """
        # Build query with eager loading to avoid N+1 queries
        query = select(RefundRecord).options(selectinload(RefundRecord.operator))

        # Add status filter
        if status and status != "all":
            query = query.where(RefundRecord.status == status)

        # Add search filter (search operator name or refund ID)
        if search:
            # Join with operator table to search by operator name
            query = query.join(RefundRecord.operator)
            # Search in operator full_name or refund ID (using CAST to text for UUID)
            from sqlalchemy import or_, cast, String
            query = query.where(
                or_(
                    OperatorAccount.full_name.ilike(f"%{search}%"),
                    cast(RefundRecord.id, String).ilike(f"%{search}%")
                )
            )

        # Order by created_at desc (newest first)
        query = query.order_by(desc(RefundRecord.created_at))

        # Get total count
        count_query = select(func.count()).select_from(RefundRecord)
        if status and status != "all":
            count_query = count_query.where(RefundRecord.status == status)
        if search:
            count_query = count_query.join(OperatorAccount)
            from sqlalchemy import or_, cast, String
            count_query = count_query.where(
                or_(
                    OperatorAccount.full_name.ilike(f"%{search}%"),
                    cast(RefundRecord.id, String).ilike(f"%{search}%")
                )
            )

        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query with operator relationship loaded
        result = await self.db.execute(query)
        refunds = result.scalars().all()

        # Convert to response items
        items = []
        for refund in refunds:
            # Operator relation already loaded via selectinload
            # Get current balance
            operator = refund.operator
            current_balance = str(operator.balance) if operator else "0.00"

            # Generate refund ID (format: RFD_YYYYMMDD_XXXXX)
            refund_created_time = refund.created_at
            refund_id = f"RFD_{refund_created_time.strftime('%Y%m%d')}_{str(refund.id)[:5].upper()}"

            items.append(RefundItemFinance(
                id=str(refund.id),
                refund_id=refund_id,
                operator_id=str(refund.operator_id),
                operator_name=operator.full_name if operator else "Unknown",
                operator_category=operator.customer_tier if operator else None,
                requested_amount=str(refund.requested_amount),
                current_balance=current_balance,
                actual_refund_amount=str(refund.actual_amount) if refund.actual_amount else None,
                status=refund.status,
                reason=refund.refund_reason,
                reject_reason=refund.reject_reason,
                reviewed_by=str(refund.reviewed_by) if refund.reviewed_by else None,
                reviewed_at=refund.reviewed_at,
                created_at=refund.created_at
            ))

        return RefundListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items
        )

    async def get_refund_details(
        self,
        refund_id: str
    ) -> RefundDetailsResponse:
        """Get detailed refund application info.

        Args:
            refund_id: Refund application ID

        Returns:
            RefundDetailsResponse: Detailed refund info with operator finance data

        Raises:
            NotFoundException: If refund not found
            BadRequestException: If refund ID format invalid
        """
        # Convert to UUID
        try:
            refund_uuid = PyUUID(refund_id)
        except ValueError:
            raise BadRequestException("Invalid refund ID format")

        # Find refund
        result = await self.db.execute(
            select(RefundRecord).where(RefundRecord.id == refund_uuid)
        )
        refund = result.scalar_one_or_none()

        if not refund:
            raise NotFoundException("Refund application not found")

        # Ensure operator relation is loaded
        if not refund.operator:
            await self.db.refresh(refund, ['operator'])

        operator = refund.operator

        # Get operator finance details
        operator_finance = await self._get_operator_finance_details(refund.operator_id)

        # Generate refund ID (format: RFD_YYYYMMDD_XXXXX)
        refund_created_time = refund.created_at
        refund_id = f"RFD_{refund_created_time.strftime('%Y%m%d')}_{str(refund.id)[:5].upper()}"

        # Build response
        return RefundDetailsResponse(
            refund_id=refund_id,
            operator_id=str(refund.operator_id),
            operator_name=operator.full_name if operator else "Unknown",
            operator_category=operator.customer_tier if operator else None,
            requested_amount=str(refund.requested_amount),
            current_balance=str(operator.balance) if operator else "0.00",
            actual_refund_amount=str(refund.actual_amount) if refund.actual_amount else None,
            status=refund.status,
            reason=refund.refund_reason,
            reject_reason=refund.reject_reason,
            reviewed_by=str(refund.reviewed_by) if refund.reviewed_by else None,
            reviewed_at=refund.reviewed_at,
            created_at=refund.created_at,
            operator_finance=operator_finance
        )

    async def approve_refund(
        self,
        refund_id: str,
        finance_id: PyUUID,
        note: Optional[str] = None
    ) -> RefundApproveResponse:
        """Approve refund application.

        Args:
            refund_id: Refund application ID
            finance_id: Finance staff ID performing the approval
            note: Optional approval note

        Returns:
            RefundApproveResponse: Approval result with refund details

        Raises:
            NotFoundException: If refund not found
            BadRequestException: If refund already reviewed or validation fails
        """
        # Convert to UUID
        try:
            refund_uuid = PyUUID(refund_id)
        except ValueError:
            raise BadRequestException("Invalid refund ID format")

        # Find refund
        result = await self.db.execute(
            select(RefundRecord).where(RefundRecord.id == refund_uuid)
        )
        refund = result.scalar_one_or_none()

        if not refund:
            raise NotFoundException("Refund application not found")

        # Check if already reviewed
        if refund.status != "pending":
            raise BadRequestException(f"Refund already {refund.status}")

        # Ensure operator relation is loaded
        if not refund.operator:
            await self.db.refresh(refund, ['operator'])

        operator = refund.operator

        # Get current balance and requested amount
        current_balance = operator.balance
        requested_amount = refund.requested_amount

        # Check if there's balance to refund
        if current_balance <= 0:
            raise BadRequestException("No balance available for refund")

        # Actual refund amount is the minimum of requested amount and current balance
        # This ensures we don't refund more than requested or more than available
        actual_refund_amount = min(requested_amount, current_balance)

        # Update refund record
        refund.status = "approved"
        refund.reviewed_by = finance_id
        refund.reviewed_at = datetime.now(timezone.utc)
        refund.actual_amount = actual_refund_amount

        # Subtract refund amount from operator balance (refund = withdraw money to bank)
        # When finance approves refund, money is transferred to operator's bank account
        # So the balance in system should decrease
        balance_before = current_balance
        operator.balance = current_balance - actual_refund_amount
        balance_after = operator.balance

        # Create transaction record
        # For refund transactions, amount is stored as positive value
        # Constraint: balance_after = balance_before - amount (for refunds)
        transaction = TransactionRecord(
            operator_id=refund.operator_id,
            transaction_type="refund",
            amount=actual_refund_amount,  # Positive value for refund amount
            balance_before=balance_before,
            balance_after=balance_after,
            description=f"退款审核通过: {note}" if note else "退款审核通过",
            related_refund_id=refund.id
        )
        self.db.add(transaction)

        # Record audit log
        audit_service = AuditLogService(self.db)
        await audit_service.log_refund_approve(
            finance_id=finance_id,
            refund_id=refund.id,
            operator_id=operator.id,
            operator_name=operator.username,
            refund_amount=str(actual_refund_amount),
            note=note
        )

        # Send notification to operator
        message_service = MessageService(self.db)
        await message_service.create_refund_approved_notification(
            operator_id=operator.id,
            refund_id=refund.id,
            refund_amount=str(refund.requested_amount),
            actual_amount=str(actual_refund_amount),
            note=note
        )

        # Commit changes
        await self.db.commit()
        await self.db.refresh(refund)

        # Generate refund ID (format: RFD_YYYYMMDD_XXXXX)
        refund_created_time = refund.created_at
        refund_id = f"RFD_{refund_created_time.strftime('%Y%m%d')}_{str(refund.id)[:5].upper()}"

        # Return response
        return RefundApproveResponse(
            refund_id=refund_id,
            requested_amount=str(refund.requested_amount),
            actual_refund_amount=str(actual_refund_amount),
            balance_after=str(balance_after)
        )

    async def reject_refund(
        self,
        refund_id: str,
        finance_id: PyUUID,
        reason: str
    ) -> None:
        """Reject refund application.

        Args:
            refund_id: Refund application ID
            finance_id: Finance staff ID performing the rejection
            reason: Rejection reason (10-200 characters)

        Raises:
            NotFoundException: If refund not found
            BadRequestException: If refund already reviewed or validation fails
        """
        # Validate reason length
        if len(reason) < 1 or len(reason) > 200:
            raise BadRequestException("Rejection reason must be between 1 and 200 characters")

        # Convert to UUID
        try:
            refund_uuid = PyUUID(refund_id)
        except ValueError:
            raise BadRequestException("Invalid refund ID format")

        # Find refund
        result = await self.db.execute(
            select(RefundRecord).where(RefundRecord.id == refund_uuid)
        )
        refund = result.scalar_one_or_none()

        if not refund:
            raise NotFoundException("Refund application not found")

        # Check if already reviewed
        if refund.status != "pending":
            raise BadRequestException(f"Refund already {refund.status}")

        # Ensure operator relation is loaded
        if not refund.operator:
            await self.db.refresh(refund, ['operator'])

        operator = refund.operator

        # Update refund record
        refund.status = "rejected"
        refund.reviewed_by = finance_id
        refund.reviewed_at = datetime.now(timezone.utc)
        refund.reject_reason = reason

        # Record audit log
        audit_service = AuditLogService(self.db)
        await audit_service.log_refund_reject(
            finance_id=finance_id,
            refund_id=refund.id,
            operator_id=operator.id,
            operator_name=operator.username,
            refund_amount=str(refund.requested_amount),
            reject_reason=reason
        )

        # Send notification to operator
        message_service = MessageService(self.db)
        await message_service.create_refund_rejected_notification(
            operator_id=operator.id,
            refund_id=refund.id,
            refund_amount=str(refund.requested_amount),
            reject_reason=reason
        )

        # Commit changes
        await self.db.commit()

    async def _get_operator_finance_details(
        self,
        operator_id: PyUUID
    ) -> CustomerFinanceDetails:
        """Get operator's detailed finance information (internal helper).

        Args:
            operator_id: Operator ID

        Returns:
            CustomerFinanceDetails: Operator finance details
        """
        # Find operator
        result = await self.db.execute(
            select(OperatorAccount).where(OperatorAccount.id == operator_id)
        )
        operator = result.scalar_one_or_none()

        if not operator:
            raise NotFoundException("Operator not found")

        # Calculate total recharged (sum of recharge transactions)
        recharge_result = await self.db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                and_(
                    TransactionRecord.operator_id == operator_id,
                    TransactionRecord.transaction_type == "recharge"
                )
            )
        )
        total_recharged = recharge_result.scalar() or Decimal("0.00")

        # Calculate total consumed (sum of consumption transactions)
        consumption_result = await self.db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                and_(
                    TransactionRecord.operator_id == operator_id,
                    TransactionRecord.transaction_type == "consumption"
                )
            )
        )
        total_consumed = consumption_result.scalar() or Decimal("0.00")

        # Calculate total refunded (sum of refund transactions)
        refund_result = await self.db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                and_(
                    TransactionRecord.operator_id == operator_id,
                    TransactionRecord.transaction_type == "refund"
                )
            )
        )
        total_refunded = refund_result.scalar() or Decimal("0.00")

        # Get total sessions count
        # TODO: Implement when usage records are available
        total_sessions = 0

        # Get first transaction time
        first_tx_result = await self.db.execute(
            select(TransactionRecord.created_at)
            .where(TransactionRecord.operator_id == operator_id)
            .order_by(TransactionRecord.created_at.asc())
            .limit(1)
        )
        first_transaction_at = first_tx_result.scalar()

        # Get last transaction time
        last_tx_result = await self.db.execute(
            select(TransactionRecord.created_at)
            .where(TransactionRecord.operator_id == operator_id)
            .order_by(TransactionRecord.created_at.desc())
            .limit(1)
        )
        last_transaction_at = last_tx_result.scalar()

        return CustomerFinanceDetails(
            operator_id=str(operator.id),
            operator_name=operator.full_name,
            category=operator.customer_tier,
            current_balance=str(operator.balance),
            total_recharged=str(total_recharged),
            total_consumed=str(total_consumed),
            total_refunded=str(total_refunded),
            total_sessions=total_sessions,
            first_transaction_at=first_transaction_at or datetime.now(timezone.utc),
            last_transaction_at=last_transaction_at
        )
