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
    "/operators",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get Operators List",
    description="Get list of all operators with search and filter capabilities",
)
async def get_operators(
    token: CurrentUserToken,
    db: DatabaseSession,
    search: Optional[str] = Query(None, description="Search by username, full_name, email, or phone"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: active/inactive/locked"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict:
    """Get operators list for admin.

    Args:
        token: Current admin token (for authentication)
        db: Database session
        search: Search keyword
        status_filter: Optional status filter
        page: Page number
        page_size: Items per page

    Returns:
        dict: Paginated list of operators
    """
    service = AdminService(db)
    return await service.get_operators(
        search=search,
        status=status_filter,
        page=page,
        page_size=page_size
    )


@router.get(
    "/applications",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get Applications List",
    description="Get list of all applications with search capability",
)
async def get_applications(
    token: CurrentUserToken,
    db: DatabaseSession,
    search: Optional[str] = Query(None, description="Search by app_code or app_name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict:
    """Get applications list for admin.

    Args:
        token: Current admin token (for authentication)
        db: Database session
        search: Search keyword
        page: Page number
        page_size: Items per page

    Returns:
        dict: Paginated list of applications
    """
    service = AdminService(db)
    return await service.get_applications(
        search=search,
        page=page,
        page_size=page_size
    )


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


# ==================== Application Management APIs (T141, T143, T144) ====================

@router.post(
    "/applications",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create Application",
    description="Create a new application (admin only)",
)
async def create_application(
    app_data: dict,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> dict:
    """Create a new application.

    Args:
        app_data: Application creation data
        token: Current admin token
        db: Database session

    Returns:
        dict: Created application data
    """
    admin_id = get_token_subject(token)
    service = AdminService(db)

    return await service.create_application(
        admin_id=admin_id,
        app_code=app_data["app_code"],
        app_name=app_data["app_name"],
        description=app_data.get("description"),
        price_per_player=app_data["price_per_player"],
        min_players=app_data["min_players"],
        max_players=app_data["max_players"]
    )


@router.put(
    "/applications/{app_id}/price",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Update Application Price",
    description="Update application price per player",
)
async def update_application_price(
    app_id: str,
    price_data: dict,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> dict:
    """Update application price.

    Args:
        app_id: Application ID
        price_data: Price update data {"new_price": float}
        token: Current admin token
        db: Database session

    Returns:
        dict: Updated application data
    """
    service = AdminService(db)
    return await service.update_application_price(
        app_id=app_id,
        new_price=price_data["new_price"]
    )


@router.put(
    "/applications/{app_id}/player-range",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Update Player Range",
    description="Update application player range (min/max players)",
)
async def update_player_range(
    app_id: str,
    range_data: dict,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> dict:
    """Update application player range.

    Args:
        app_id: Application ID
        range_data: Range data {"min_players": int, "max_players": int}
        token: Current admin token
        db: Database session

    Returns:
        dict: Updated application data
    """
    service = AdminService(db)
    return await service.update_player_range(
        app_id=app_id,
        min_players=range_data["min_players"],
        max_players=range_data["max_players"]
    )


# ==================== Authorization Management APIs (T145, T146) ====================

@router.post(
    "/operators/{operator_id}/applications",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Authorize Application",
    description="Authorize an application for an operator",
)
async def authorize_application(
    operator_id: str,
    auth_data: dict,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> dict:
    """Authorize an application for an operator.

    Args:
        operator_id: Operator ID
        auth_data: Authorization data {"application_id": str, "expires_at": Optional[str]}
        token: Current admin token
        db: Database session

    Returns:
        dict: Authorization data
    """
    from datetime import datetime

    admin_id = get_token_subject(token)
    service = AdminService(db)

    expires_at = None
    if auth_data.get("expires_at"):
        expires_at = datetime.fromisoformat(auth_data["expires_at"])

    return await service.authorize_application(
        operator_id=operator_id,
        application_id=auth_data["application_id"],
        admin_id=admin_id,
        expires_at=expires_at
    )


@router.delete(
    "/operators/{operator_id}/applications/{app_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Revoke Authorization",
    description="Revoke an application authorization for an operator",
)
async def revoke_authorization(
    operator_id: str,
    app_id: str,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> dict:
    """Revoke an application authorization.

    Args:
        operator_id: Operator ID
        app_id: Application ID
        token: Current admin token
        db: Database session

    Returns:
        dict: Revoked authorization data
    """
    service = AdminService(db)
    return await service.revoke_authorization(
        operator_id=operator_id,
        application_id=app_id
    )


# ==================== Dashboard Statistics API ====================

@router.get(
    "/dashboard/stats",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard Statistics",
    description="Get dashboard statistics for admin panel",
)
async def get_dashboard_stats(
    token: CurrentUserToken,
    db: DatabaseSession,
) -> dict:
    """Get dashboard statistics.

    Args:
        token: Current admin token
        db: Database session

    Returns:
        dict: Dashboard statistics including counts and revenue
    """
    from sqlalchemy import select, func
    from datetime import datetime, timedelta
    from ...models.operator import OperatorAccount
    from ...models.application import Application
    from ...models.app_request import ApplicationRequest
    from ...models.transaction import TransactionRecord

    # Get operators count
    operators_result = await db.execute(
        select(func.count(OperatorAccount.id)).where(
            OperatorAccount.deleted_at.is_(None)
        )
    )
    operators_count = operators_result.scalar() or 0

    # Get applications count
    apps_result = await db.execute(
        select(func.count(Application.id)).where(
            Application.is_active == True
        )
    )
    applications_count = apps_result.scalar() or 0

    # Get pending requests count
    pending_result = await db.execute(
        select(func.count(ApplicationRequest.id)).where(
            ApplicationRequest.status == "pending"
        )
    )
    pending_requests_count = pending_result.scalar() or 0

    # Get today's transactions count and revenue
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    transactions_result = await db.execute(
        select(
            func.count(TransactionRecord.id),
            func.coalesce(func.sum(TransactionRecord.amount), 0)
        ).where(
            TransactionRecord.created_at >= today_start,
            TransactionRecord.transaction_type == "consumption"
        )
    )
    row = transactions_result.first()
    today_transactions_count = row[0] if row else 0
    today_revenue = str(row[1]) if row else "0.00"

    return {
        "operators_count": operators_count,
        "applications_count": applications_count,
        "pending_requests_count": pending_requests_count,
        "today_transactions_count": today_transactions_count,
        "today_revenue": today_revenue,
    }
