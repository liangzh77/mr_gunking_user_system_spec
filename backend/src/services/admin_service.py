"""Admin business operations service.

This service handles admin operations like reviewing application authorization requests.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID as PyUUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import BadRequestException, NotFoundException
from ..models.app_request import ApplicationRequest
from ..models.authorization import OperatorAppAuthorization
from ..models.application import Application
from ..schemas.operator import ApplicationRequestItem, ApplicationRequestListResponse


class AdminService:
    """Admin business operations service."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_application_requests(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> ApplicationRequestListResponse:
        """Get application authorization requests list.

        Args:
            status: Filter by status (pending/approved/rejected), None for all
            page: Page number (starts from 1)
            page_size: Items per page

        Returns:
            ApplicationRequestListResponse: Paginated list of requests
        """
        # Build query
        query = select(ApplicationRequest)

        # Add status filter if provided
        if status:
            query = query.where(ApplicationRequest.status == status)

        # Order by created_at desc (newest first)
        query = query.order_by(desc(ApplicationRequest.created_at))

        # Get total count
        count_result = await self.db.execute(
            select(ApplicationRequest).where(
                ApplicationRequest.status == status if status else True
            )
        )
        total = len(count_result.scalars().all())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        requests = result.scalars().all()

        # Convert to response items
        items = []
        for req in requests:
            # Ensure application is loaded
            if not req.application:
                await self.db.refresh(req, ['application'])

            items.append(ApplicationRequestItem(
                request_id=str(req.id),
                app_id=str(req.application_id),
                app_code=req.application.app_code if req.application else "unknown",
                app_name=req.application.app_name if req.application else "Unknown",
                reason=req.reason,
                status=req.status,
                reject_reason=req.reject_reason,
                reviewed_by=str(req.reviewed_by) if req.reviewed_by else None,
                reviewed_at=req.reviewed_at,
                created_at=req.created_at
            ))

        return ApplicationRequestListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items
        )

    async def review_application_request(
        self,
        request_id: str,
        admin_id: PyUUID,
        action: str,
        reject_reason: Optional[str] = None
    ) -> ApplicationRequestItem:
        """Review (approve/reject) an application authorization request.

        Args:
            request_id: Application request ID
            admin_id: Admin ID performing the review
            action: "approve" or "reject"
            reject_reason: Reason for rejection (required if action is reject)

        Returns:
            ApplicationRequestItem: Updated request item

        Raises:
            NotFoundException: If request not found
            BadRequestException: If request already reviewed or validation fails
        """
        # Validate action
        if action not in ["approve", "reject"]:
            raise BadRequestException("Invalid action. Must be 'approve' or 'reject'")

        # If rejecting, require reject_reason
        if action == "reject" and not reject_reason:
            raise BadRequestException("Reject reason is required when action is 'reject'")

        # Find the request
        try:
            request_uuid = PyUUID(request_id)
        except ValueError:
            raise BadRequestException("Invalid request ID format")

        result = await self.db.execute(
            select(ApplicationRequest).where(ApplicationRequest.id == request_uuid)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise NotFoundException("Application request not found")

        # Check if already reviewed
        if request.status != "pending":
            raise BadRequestException(f"Request already {request.status}")

        # Update request status
        request.status = "approved" if action == "approve" else "rejected"
        request.reviewed_by = admin_id
        request.reviewed_at = datetime.now(timezone.utc)

        if action == "reject":
            request.reject_reason = reject_reason

        # If approved, create authorization
        if action == "approve":
            # Check if authorization already exists
            auth_result = await self.db.execute(
                select(OperatorAppAuthorization).where(
                    and_(
                        OperatorAppAuthorization.operator_id == request.operator_id,
                        OperatorAppAuthorization.application_id == request.application_id,
                        OperatorAppAuthorization.is_active == True
                    )
                )
            )
            existing_auth = auth_result.scalar_one_or_none()

            if not existing_auth:
                # Create new authorization
                authorization = OperatorAppAuthorization(
                    operator_id=request.operator_id,
                    application_id=request.application_id,
                    authorized_by=admin_id,
                    application_request_id=request.id,
                    is_active=True,
                    authorized_at=datetime.now(timezone.utc),
                    expires_at=None  # Permanent authorization
                )
                self.db.add(authorization)

        # Commit changes
        await self.db.commit()
        await self.db.refresh(request)

        # Load application relation if not loaded
        if not request.application:
            await self.db.refresh(request, ['application'])

        # Return updated request
        return ApplicationRequestItem(
            request_id=str(request.id),
            app_id=str(request.application_id),
            app_code=request.application.app_code if request.application else "unknown",
            app_name=request.application.app_name if request.application else "Unknown",
            reason=request.reason,
            status=request.status,
            reject_reason=request.reject_reason,
            reviewed_by=str(request.reviewed_by) if request.reviewed_by else None,
            reviewed_at=request.reviewed_at,
            created_at=request.created_at
        )
