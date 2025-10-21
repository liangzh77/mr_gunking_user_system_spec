"""Admin business operations API endpoints.

This module handles admin operations like reviewing application authorization requests.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import CurrentUserToken, DatabaseSession
from ...schemas.admin import ApplicationRequestReviewRequest
from ...schemas.admin_operator import CreateOperatorRequest, OperatorDetailResponse
from ...schemas.operator import ApplicationRequestItem, ApplicationRequestListResponse
from ...schemas.common import MessageResponse
from ...schemas.site import SiteCreateRequest, SiteUpdateRequest, SiteListResponse, SiteItem
from ...services.admin_service import AdminService
from ...core import get_token_subject

router = APIRouter(prefix="/admins", tags=["Admin Operations"])


@router.post(
    "/operators",
    response_model=OperatorDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Operator",
    description="Create a new operator account (admin only)",
)
async def create_operator(
    operator_data: CreateOperatorRequest,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> OperatorDetailResponse:
    """Create a new operator account.

    Args:
        operator_data: Operator creation data
        token: Current admin token
        db: Database session

    Returns:
        OperatorDetailResponse: Created operator data
    """
    admin_id = get_token_subject(token)
    service = AdminService(db)

    operator_dict = await service.create_operator(
        admin_id=admin_id,
        username=operator_data.username,
        password=operator_data.password,
        full_name=operator_data.full_name,
        email=operator_data.email,
        phone=operator_data.phone,
        customer_tier=operator_data.customer_tier
    )

    return OperatorDetailResponse.model_validate(operator_dict)


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


# ==================== 运营点管理API ====================


@router.get(
    "/sites",
    response_model=SiteListResponse,
    status_code=status.HTTP_200_OK,
    summary="获取运营点列表",
    description="获取所有运营点列表，支持分页和搜索",
)
async def get_sites(
    token: CurrentUserToken,
    db: DatabaseSession,
    search: Optional[str] = Query(None, description="搜索运营点名称或地址"),
    operator_id: Optional[str] = Query(None, description="按运营商ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
) -> SiteListResponse:
    """获取运营点列表

    Args:
        token: 当前管理员token
        db: 数据库会话
        search: 搜索关键词
        operator_id: 运营商ID筛选
        page: 页码
        page_size: 每页条数

    Returns:
        SiteListResponse: 分页的运营点列表
    """
    service = AdminService(db)
    return await service.get_sites(
        search=search,
        operator_id=operator_id,
        page=page,
        page_size=page_size
    )


@router.post(
    "/sites",
    response_model=SiteItem,
    status_code=status.HTTP_201_CREATED,
    summary="创建运营点",
    description="创建新的运营点",
)
async def create_site(
    site_data: SiteCreateRequest,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> SiteItem:
    """创建运营点

    Args:
        site_data: 运营点创建数据
        token: 当前管理员token
        db: 数据库会话

    Returns:
        SiteItem: 创建的运营点
    """
    admin_id = get_token_subject(token)
    service = AdminService(db)

    return await service.create_site(
        admin_id=admin_id,
        name=site_data.name,
        address=site_data.address,
        description=site_data.description,
        operator_id=site_data.operator_id,
        contact_person=site_data.contact_person,
        contact_phone=site_data.contact_phone,
        server_identifier=site_data.server_identifier
    )


@router.put(
    "/sites/{site_id}",
    response_model=SiteItem,
    status_code=status.HTTP_200_OK,
    summary="更新运营点",
    description="更新运营点信息",
)
async def update_site(
    site_id: str,
    site_data: SiteUpdateRequest,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> SiteItem:
    """更新运营点

    Args:
        site_id: 运营点ID
        site_data: 运营点更新数据
        token: 当前管理员token
        db: 数据库会话

    Returns:
        SiteItem: 更新后的运营点
    """
    admin_id = get_token_subject(token)
    service = AdminService(db)

    return await service.update_site(
        site_id=site_id,
        admin_id=admin_id,
        **site_data.model_dump(exclude_unset=True)
    )


@router.delete(
    "/sites/{site_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="删除运营点",
    description="删除运营点（软删除）",
)
async def delete_site(
    site_id: str,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> MessageResponse:
    """删除运营点

    Args:
        site_id: 运营点ID
        token: 当前管理员token
        db: 数据库会话

    Returns:
        MessageResponse: 删除结果消息
    """
    admin_id = get_token_subject(token)
    service = AdminService(db)

    await service.delete_site(site_id=site_id, admin_id=admin_id)
    return MessageResponse(message="运营点删除成功")
