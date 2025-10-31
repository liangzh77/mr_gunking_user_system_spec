"""Admin business operations API endpoints.

This module handles admin operations like reviewing application authorization requests.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import CurrentUserToken, DatabaseSession
from ...schemas.admin import ApplicationRequestReviewRequest
from ...schemas.admin_operator import (
    CreateOperatorRequest,
    UpdateOperatorRequest,
    OperatorDetailResponse,
    OperatorApiKeyResponse,
)
from ...schemas.admin_application import (
    CreateApplicationRequest,
    UpdateApplicationRequest,
    ApplicationResponse,
    ApplicationListResponse,
    AuthorizeApplicationRequest,
    AuthorizationResponse,
)
from ...schemas.operator import ApplicationRequestItem, ApplicationRequestListResponse
from ...schemas.common import MessageResponse
from ...schemas.site import SiteCreateRequest, SiteUpdateRequest, SiteListResponse, SiteItem
from ...services.admin_service import AdminService
from ...services.admin_permissions import AdminPermissionChecker
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

    # 权限检查：需要创建运营商权限
    await AdminPermissionChecker.require_permission(
        db, admin_id, "operator:create"
    )

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


@router.put(
    "/operators/{operator_id}",
    response_model=OperatorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Operator",
    description="Update operator account information",
)
async def update_operator(
    operator_id: str,
    operator_data: UpdateOperatorRequest,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> OperatorDetailResponse:
    """Update operator account information.

    Args:
        operator_id: Operator ID
        operator_data: Operator update data
        token: Current admin token
        db: Database session

    Returns:
        OperatorDetailResponse: Updated operator data
    """
    from uuid import UUID

    try:
        op_uuid = UUID(operator_id)
    except ValueError:
        from ...core import BadRequestException
        raise BadRequestException("Invalid operator ID format")

    admin_id = get_token_subject(token)

    # 权限检查：需要编辑运营商权限
    await AdminPermissionChecker.require_permission(
        db, admin_id, "operator:edit"
    )

    service = AdminService(db)

    operator_dict = await service.update_operator(
        operator_id=op_uuid,
        full_name=operator_data.full_name,
        email=operator_data.email,
        phone=operator_data.phone,
        customer_tier=operator_data.customer_tier,
        is_active=operator_data.is_active,
    )

    return OperatorDetailResponse.model_validate(operator_dict)


@router.delete(
    "/operators/{operator_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Operator",
    description="Delete operator account (soft delete)",
)
async def delete_operator(
    operator_id: str,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> MessageResponse:
    """Delete operator account.

    Args:
        operator_id: Operator ID
        token: Current admin token
        db: Database session

    Returns:
        MessageResponse: Success message
    """
    from uuid import UUID

    try:
        op_uuid = UUID(operator_id)
    except ValueError:
        from ...core import BadRequestException
        raise BadRequestException("Invalid operator ID format")

    admin_id = get_token_subject(token)

    # 权限检查：需要删除运营商权限
    await AdminPermissionChecker.require_permission(
        db, admin_id, "operator:delete"
    )

    service = AdminService(db)

    result = await service.delete_operator(operator_id=op_uuid)

    return MessageResponse(
        success=result["success"],
        message=result["message"]
    )


@router.get(
    "/operators/{operator_id}/api-key",
    response_model=OperatorApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Operator API Key",
    description="Get operator API key (admin only, requires operator:view permission)",
)
async def get_operator_api_key(
    operator_id: str,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> OperatorApiKeyResponse:
    """Get operator API key.

    Args:
        operator_id: Operator ID
        token: Current admin token
        db: Database session

    Returns:
        OperatorApiKeyResponse: Operator API key information
    """
    from uuid import UUID

    try:
        op_uuid = UUID(operator_id)
    except ValueError:
        from ...core import BadRequestException
        raise BadRequestException("Invalid operator ID format")

    admin_id = get_token_subject(token)

    # 权限检查：需要查看运营商权限
    await AdminPermissionChecker.require_permission(
        db, admin_id, "operator:view"
    )

    service = AdminService(db)
    api_key_info = await service.get_operator_api_key(operator_id=op_uuid)

    return OperatorApiKeyResponse.model_validate(api_key_info)


@router.get(
    "/applications",
    response_model=ApplicationListResponse,
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
) -> ApplicationListResponse:
    """Get applications list for admin.

    Args:
        token: Current admin token (for authentication)
        db: Database session
        search: Search keyword
        page: Page number
        page_size: Items per page

    Returns:
        ApplicationListResponse: Paginated list of applications
    """
    from math import ceil

    service = AdminService(db)
    applications, total = await service.get_applications(
        search=search,
        page=page,
        page_size=page_size
    )

    # Convert Application models to ApplicationResponse
    items = [ApplicationResponse.model_validate(app) for app in applications]

    # Calculate total pages
    total_pages = ceil(total / page_size) if total > 0 else 0

    return ApplicationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
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
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Application",
    description="Create a new application (admin only)",
)
async def create_application(
    app_data: CreateApplicationRequest,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> ApplicationResponse:
    """Create a new application.

    Args:
        app_data: Application creation data
        token: Current admin token
        db: Database session

    Returns:
        ApplicationResponse: Created application data
    """
    admin_id = get_token_subject(token)
    service = AdminService(db)

    app = await service.create_application(
        admin_id=admin_id,
        app_name=app_data.app_name,
        unit_price=app_data.unit_price,
        min_players=app_data.min_players,
        max_players=app_data.max_players,
        description=app_data.description,
    )

    return ApplicationResponse.model_validate(app)


@router.put(
    "/applications/{app_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Application",
    description="Update application basic information (excludes price)",
)
async def update_application(
    app_id: str,
    app_data: UpdateApplicationRequest,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> ApplicationResponse:
    """Update application basic information.

    Args:
        app_id: Application ID (UUID string)
        app_data: Application update data
        token: Current admin token
        db: Database session

    Returns:
        ApplicationResponse: Updated application data
    """
    from uuid import UUID

    try:
        app_uuid = UUID(app_id)
    except ValueError:
        from ...core import BadRequestException
        raise BadRequestException("Invalid application ID format")

    service = AdminService(db)

    app = await service.update_application(
        app_id=app_uuid,
        app_name=app_data.app_name,
        min_players=app_data.min_players,
        max_players=app_data.max_players,
        description=app_data.description,
        is_active=app_data.is_active,
    )

    return ApplicationResponse.model_validate(app)


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
    response_model=AuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Authorize Application",
    description="Authorize an application for an operator",
)
async def authorize_application(
    operator_id: str,
    auth_data: AuthorizeApplicationRequest,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> AuthorizationResponse:
    """Authorize an application for an operator.

    Args:
        operator_id: Operator ID (UUID string)
        auth_data: Authorization request data
        token: Current admin token
        db: Database session

    Returns:
        AuthorizationResponse: Authorization data with operator and app names
    """
    from uuid import UUID

    try:
        operator_uuid = UUID(operator_id)
    except ValueError:
        from ...core import BadRequestException
        raise BadRequestException("Invalid operator ID format")

    admin_id = get_token_subject(token)
    service = AdminService(db)

    authorization = await service.authorize_application(
        operator_id=operator_uuid,
        application_id=auth_data.application_id,
        admin_id=admin_id,
        expires_at=auth_data.expires_at,
        application_request_id=auth_data.application_request_id,
    )

    # Build response with operator and app names from relationships
    return AuthorizationResponse(
        id=authorization.id,
        operator_id=authorization.operator_id,
        application_id=authorization.application_id,
        operator_name=authorization.operator.full_name,
        app_name=authorization.application.app_name,
        authorized_at=authorization.authorized_at,
        expires_at=authorization.expires_at,
        authorized_by=authorization.authorized_by,
        application_request_id=authorization.application_request_id,
        is_active=authorization.is_active,
        created_at=authorization.created_at,
        updated_at=authorization.updated_at,
    )


@router.delete(
    "/operators/{operator_id}/applications/{app_id}",
    response_model=AuthorizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke Authorization",
    description="Revoke an application authorization for an operator",
)
async def revoke_authorization(
    operator_id: str,
    app_id: str,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> AuthorizationResponse:
    """Revoke an application authorization.

    Args:
        operator_id: Operator ID (UUID string)
        app_id: Application ID (UUID string)
        token: Current admin token
        db: Database session

    Returns:
        AuthorizationResponse: Revoked authorization data
    """
    from uuid import UUID

    try:
        operator_uuid = UUID(operator_id)
        app_uuid = UUID(app_id)
    except ValueError:
        from ...core import BadRequestException
        raise BadRequestException("Invalid ID format")

    service = AdminService(db)
    authorization = await service.revoke_authorization(
        operator_id=operator_uuid,
        application_id=app_uuid
    )

    # Build response with operator and app names from relationships
    return AuthorizationResponse(
        id=authorization.id,
        operator_id=authorization.operator_id,
        application_id=authorization.application_id,
        operator_name=authorization.operator.full_name,
        app_name=authorization.application.app_name,
        authorized_at=authorization.authorized_at,
        expires_at=authorization.expires_at,
        authorized_by=authorization.authorized_by,
        application_request_id=authorization.application_request_id,
        is_active=authorization.is_active,
        created_at=authorization.created_at,
        updated_at=authorization.updated_at,
    )


@router.get(
    "/operators/{operator_id}/applications",
    response_model=list,
    status_code=status.HTTP_200_OK,
    summary="Get Operator Authorized Applications",
    description="Get list of applications authorized for an operator",
)
async def get_operator_applications(
    operator_id: str,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> list:
    """Get authorized applications for an operator.

    Args:
        operator_id: Operator ID (UUID string)
        token: Current admin token
        db: Database session

    Returns:
        list: List of authorized application IDs
    """
    from uuid import UUID
    from sqlalchemy import select
    from ...models.authorization import OperatorAppAuthorization

    try:
        operator_uuid = UUID(operator_id)
    except ValueError:
        from ...core import BadRequestException
        raise BadRequestException("Invalid operator ID format")

    # Query authorized applications for this operator
    stmt = select(OperatorAppAuthorization.application_id).where(
        OperatorAppAuthorization.operator_id == operator_uuid,
        OperatorAppAuthorization.is_active == True
    )
    result = await db.execute(stmt)
    app_ids = result.scalars().all()

    # Convert UUIDs to strings
    return [str(app_id) for app_id in app_ids]


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


# ==================== 交易记录管理API ====================


@router.get(
    "/transactions",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get All Transactions",
    description="Get all transaction records with filtering and pagination",
)
async def get_transactions(
    token: CurrentUserToken,
    db: DatabaseSession,
    operator_id: Optional[str] = Query(None, description="Filter by operator ID"),
    transaction_type: Optional[str] = Query(None, description="Filter by type: recharge/consumption/refund"),
    start_time: Optional[str] = Query(None, description="Start time for filtering"),
    end_time: Optional[str] = Query(None, description="End time for filtering"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict:
    """Get all transaction records for admin.

    Args:
        token: Current admin token
        db: Database session
        operator_id: Optional operator ID filter
        transaction_type: Optional transaction type filter
        start_time: Optional start time filter
        end_time: Optional end time filter
        page: Page number
        page_size: Items per page

    Returns:
        dict: Paginated list of transactions with operator names
    """
    from uuid import UUID as PyUUID
    from sqlalchemy import select, and_, or_, func, desc
    from ...models.transaction import TransactionRecord
    from ...models.operator import OperatorAccount
    from datetime import datetime

    # Build query
    query = select(
        TransactionRecord.id,
        TransactionRecord.operator_id,
        OperatorAccount.full_name.label('operator_name'),
        TransactionRecord.transaction_type,
        TransactionRecord.amount,
        TransactionRecord.balance_after,
        TransactionRecord.description,
        TransactionRecord.created_at,
        TransactionRecord.status,
    ).join(
        OperatorAccount,
        TransactionRecord.operator_id == OperatorAccount.id
    )

    # Apply filters
    filters = []

    if operator_id:
        try:
            op_uuid = PyUUID(operator_id)
            filters.append(TransactionRecord.operator_id == op_uuid)
        except ValueError:
            pass

    if transaction_type:
        filters.append(TransactionRecord.transaction_type == transaction_type)

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            filters.append(TransactionRecord.created_at >= start_dt)
        except ValueError:
            pass

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            filters.append(TransactionRecord.created_at <= end_dt)
        except ValueError:
            pass

    if filters:
        query = query.where(and_(*filters))

    # Order by created_at descending
    query = query.order_by(desc(TransactionRecord.created_at))

    # Get total count
    count_query = select(func.count()).select_from(TransactionRecord)
    if filters:
        count_query = count_query.where(and_(*filters))

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    # Convert to response format
    items = []
    for row in rows:
        items.append({
            "id": str(row.id),
            "operator_id": str(row.operator_id),
            "operator_name": row.operator_name,
            "transaction_type": row.transaction_type,
            "amount": str(row.amount),
            "balance_after": str(row.balance_after),
            "description": row.description,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "status": row.status,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
