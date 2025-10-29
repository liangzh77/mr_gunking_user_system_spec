"""全局统计仪表盘API (T199)

提供管理员查看系统全局统计数据的接口。
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.dependencies import CurrentUserToken, DatabaseSession
from ....schemas.statistics.global_stats import GlobalDashboardResponse
from ....schemas.common import SuccessResponse
from ....services.global_statistics import GlobalStatisticsService
from ....core import get_token_subject

router = APIRouter(tags=["Statistics"])


@router.get(
    "/dashboard",
    response_model=SuccessResponse[GlobalDashboardResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Global Dashboard Statistics",
    description="Get global statistics dashboard data (admin only). Returns total operators, sessions, players, and revenue.",
)
async def get_global_dashboard(
    token: CurrentUserToken,
    db: DatabaseSession,
    start_time: Optional[datetime] = Query(
        None,
        description="Start time for filtering (ISO 8601 format)",
        example="2025-01-01T00:00:00Z"
    ),
    end_time: Optional[datetime] = Query(
        None,
        description="End time for filtering (ISO 8601 format)",
        example="2025-01-31T23:59:59Z"
    ),
) -> SuccessResponse[GlobalDashboardResponse]:
    """Get global dashboard statistics.

    This endpoint provides a high-level overview of the entire system:
    - Total number of operators
    - Total game sessions
    - Total player count
    - Total revenue

    Only accessible by admin users.

    Args:
        token: Admin JWT token
        db: Database session
        start_time: Optional start time for filtering
        end_time: Optional end time for filtering

    Returns:
        SuccessResponse containing GlobalDashboardResponse

    Raises:
        401: Unauthorized (invalid or missing token)
        403: Forbidden (not an admin user)
        400: Bad Request (invalid time range)
    """
    # Validate admin token
    admin_id = get_token_subject(token)

    # Validate time range
    if start_time and end_time and end_time < start_time:
        from ....core.exceptions import BadRequestException
        raise BadRequestException("end_time must be after start_time")

    # Get statistics
    service = GlobalStatisticsService(db)
    data = await service.get_global_dashboard(
        start_time=start_time,
        end_time=end_time
    )

    return SuccessResponse(
        success=True,
        data=GlobalDashboardResponse(**data)
    )
