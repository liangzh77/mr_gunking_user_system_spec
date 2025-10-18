"""Finance invoice review service (T171).

This service handles invoice application review operations by finance staff.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID as PyUUID

from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import NotFoundException, BadRequestException
from ..models.invoice import InvoiceRecord
from ..models.operator import OperatorAccount
from ..schemas.finance import (
    InvoiceItemFinance,
    InvoiceListResponse,
    InvoiceApproveResponse
)


class FinanceInvoiceService:
    """Finance invoice review service."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_invoices(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> InvoiceListResponse:
        """Get invoice applications list.

        Args:
            status: Filter by status (pending/approved/rejected/all)
            page: Page number (starts from 1)
            page_size: Items per page

        Returns:
            InvoiceListResponse: Paginated list of invoice applications
        """
        # Build query with eager loading to avoid N+1 queries
        query = select(InvoiceRecord).options(selectinload(InvoiceRecord.operator))

        # Add status filter
        if status and status != "all":
            query = query.where(InvoiceRecord.status == status)

        # Order by requested_at desc (newest first)
        query = query.order_by(desc(InvoiceRecord.requested_at))

        # Get total count
        count_query = select(func.count()).select_from(InvoiceRecord)
        if status and status != "all":
            count_query = count_query.where(InvoiceRecord.status == status)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query with operator relationship loaded
        result = await self.db.execute(query)
        invoices = result.scalars().all()

        # Convert to response items
        items = []
        for invoice in invoices:
            # Operator relation already loaded via selectinload
            operator = invoice.operator

            items.append(InvoiceItemFinance(
                invoice_id=str(invoice.id),
                operator_id=str(invoice.operator_id),
                operator_name=operator.full_name if operator else "Unknown",
                operator_category=operator.customer_tier if operator else None,
                amount=str(invoice.invoice_amount),
                invoice_title=invoice.invoice_title,
                tax_id=invoice.tax_id,
                email=operator.email if operator else None,
                status=invoice.status,
                pdf_url=invoice.invoice_file_url,
                reviewed_by=str(invoice.reviewed_by) if invoice.reviewed_by else None,
                reviewed_at=invoice.reviewed_at,
                created_at=invoice.requested_at
            ))

        return InvoiceListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items
        )

    async def approve_invoice(
        self,
        invoice_id: str,
        finance_id: PyUUID,
        note: Optional[str] = None
    ) -> InvoiceApproveResponse:
        """Approve invoice application and generate PDF.

        Args:
            invoice_id: Invoice application ID
            finance_id: Finance staff ID performing the approval
            note: Optional approval note

        Returns:
            InvoiceApproveResponse: Approval result with PDF URL

        Raises:
            NotFoundException: If invoice not found
            BadRequestException: If invoice already reviewed or validation fails
        """
        # Convert to UUID
        try:
            invoice_uuid = PyUUID(invoice_id)
        except ValueError:
            raise BadRequestException("Invalid invoice ID format")

        # Find invoice
        result = await self.db.execute(
            select(InvoiceRecord).where(InvoiceRecord.id == invoice_uuid)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise NotFoundException("Invoice application not found")

        # Check if already reviewed
        if invoice.status != "pending":
            raise BadRequestException(f"Invoice already {invoice.status}")

        # Update invoice record
        invoice.status = "approved"
        invoice.reviewed_by = finance_id
        invoice.reviewed_at = datetime.now(timezone.utc)
        invoice.issued_at = datetime.now(timezone.utc)

        # Generate invoice number (format: INV-YYYYMMDD-XXXXX)
        now = datetime.now(timezone.utc)
        invoice_number = f"INV-{now.strftime('%Y%m%d')}-{str(invoice.id)[:5].upper()}"
        invoice.invoice_number = invoice_number

        # Generate PDF URL (placeholder - actual PDF generation would be handled by separate service)
        # For now, create a deterministic URL
        pdf_url = f"https://api.example.com/invoices/{invoice_id}.pdf"
        invoice.invoice_file_url = pdf_url

        # Commit changes
        await self.db.commit()
        await self.db.refresh(invoice)

        # TODO: Trigger actual PDF generation asynchronously
        # This would typically involve:
        # 1. Queue a background job to generate PDF
        # 2. Upload PDF to storage (S3, etc.)
        # 3. Update invoice_file_url with actual URL

        # Return response
        return InvoiceApproveResponse(
            invoice_id=str(invoice.id),
            pdf_url=pdf_url
        )

    async def reject_invoice(
        self,
        invoice_id: str,
        finance_id: PyUUID,
        reason: str
    ) -> None:
        """Reject invoice application.

        Args:
            invoice_id: Invoice application ID
            finance_id: Finance staff ID performing the rejection
            reason: Rejection reason (10-200 characters)

        Raises:
            NotFoundException: If invoice not found
            BadRequestException: If invoice already reviewed or validation fails
        """
        # Validate reason length
        if len(reason) < 10 or len(reason) > 200:
            raise BadRequestException("Rejection reason must be between 10 and 200 characters")

        # Convert to UUID
        try:
            invoice_uuid = PyUUID(invoice_id)
        except ValueError:
            raise BadRequestException("Invalid invoice ID format")

        # Find invoice
        result = await self.db.execute(
            select(InvoiceRecord).where(InvoiceRecord.id == invoice_uuid)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise NotFoundException("Invoice application not found")

        # Check if already reviewed
        if invoice.status != "pending":
            raise BadRequestException(f"Invoice already {invoice.status}")

        # Update invoice record
        invoice.status = "rejected"
        invoice.reviewed_by = finance_id
        invoice.reviewed_at = datetime.now(timezone.utc)
        invoice.reject_reason = reason

        # Commit changes
        await self.db.commit()
