"""按应用统计API (T200)

提供按应用维度查看统计数据的接口。
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.dependencies import CurrentUserToken, DatabaseSession
from ....schemas.statistics.global_stats import CrossAnalysisResponse
from ....schemas.common import SuccessResponse
from ....services.global_statistics import GlobalStatisticsService
from ....core import get_token_subject

router = APIRouter(tags=["Statistics"])


@router.get(
    "/by-application",
    response_model=SuccessResponse[CrossAnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Statistics by Application",
    description="Get statistics grouped by application (admin only). Shows total sessions, players, and revenue for each application.",
)
async def get_app_statistics(
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
) -> SuccessResponse[CrossAnalysisResponse]:
    """Get statistics by application.

    This endpoint provides application-level statistics:
    - Application name
    - Total game sessions per application
    - Total player count per application
    - Total revenue per application
    - Average players per session

    Results are sorted by revenue in descending order.

    Only accessible by admin users.

    Args:
        token: Admin JWT token
        db: Database session
        start_time: Optional start time for filtering
        end_time: Optional end time for filtering

    Returns:
        SuccessResponse containing CrossAnalysisResponse with application dimension

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
    data = await service.get_cross_analysis(
        dimension="application",
        start_time=start_time,
        end_time=end_time
    )

    return SuccessResponse(
        success=True,
        data=CrossAnalysisResponse(**data)
    )
