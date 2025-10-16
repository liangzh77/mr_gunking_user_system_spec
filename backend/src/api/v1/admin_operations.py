"""Admin business operations API endpoints.

This module handles admin operations like reviewing application authorization requests.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import CurrentUserToken, DatabaseSession
from ...schemas.admin import ApplicationRequestReviewRequest
from ...schemas.operator import ApplicationRequestItem, ApplicationRequestListResponse
from ...schemas.common import MessageResponse
from ...services.admin_service import AdminService
from ...core import get_token_subject

router = APIRouter(prefix="/admins", tags=["Admin Operations"])


@router.get(
    "/applications/requests",
    response_model=ApplicationRequestListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Application Authorization Requests",
    description="Get list of application authorization requests (with optional status filter)",
)
async def get_application_requests(
    token: CurrentUserToken,
    db: DatabaseSession,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: pending/approved/rejected"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ApplicationRequestListResponse:
    """Get application authorization requests list.

    Args:
        token: Current admin token (for authentication)
        db: Database session
        status_filter: Optional status filter
        page: Page number
        page_size: Items per page

    Returns:
        ApplicationRequestListResponse: Paginated list of requests
    """
    service = AdminService(db)
    return await service.get_application_requests(
        status=status_filter,
        page=page,
        page_size=page_size
    )


@router.post(
    "/applications/requests/{request_id}/review",
    response_model=ApplicationRequestItem,
    status_code=status.HTTP_200_OK,
    summary="Review Application Authorization Request",
    description="Approve or reject an application authorization request",
)
async def review_application_request(
    request_id: str,
    review_data: ApplicationRequestReviewRequest,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> ApplicationRequestItem:
    """Review (approve/reject) an application authorization request.

    Args:
        request_id: Application request ID
        review_data: Review data (action and optional reject_reason)
        token: Current admin token
        db: Database session

    Returns:
        ApplicationRequestItem: Updated request item
    """
    # Get admin ID from token
    admin_id = get_token_subject(token)

    service = AdminService(db)
    return await service.review_application_request(
        request_id=request_id,
        admin_id=admin_id,
        action=review_data.action,
        reject_reason=review_data.reject_reason
    )
