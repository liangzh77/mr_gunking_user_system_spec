"""玩家数量分布统计API (T202)

提供玩家数量分布分析的接口，用于了解不同玩家数量的游戏场次分布。
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.dependencies import CurrentUserToken, DatabaseSession
from ....schemas.statistics.player_distribution import PlayerDistributionResponse
from ....schemas.common import SuccessResponse
from ....services.global_statistics import GlobalStatisticsService
from ....core import get_token_subject

router = APIRouter(tags=["Statistics"])


@router.get(
    "/player-distribution",
    response_model=SuccessResponse[PlayerDistributionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Player Distribution Statistics",
    description="Get player count distribution statistics (admin only). Shows how game sessions are distributed across different player counts.",
)
async def get_player_distribution(
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
) -> SuccessResponse[PlayerDistributionResponse]:
    """Get player count distribution statistics.

    This endpoint provides insights into player count preferences:
    - Distribution of game sessions by player count
    - Percentage breakdown (e.g., 2-player games: 25%, 3-4 player games: 50%)
    - Total revenue for each player count
    - Most common player count

    Useful for understanding game preferences and optimizing pricing strategies.

    Only accessible by admin users.

    Args:
        token: Admin JWT token
        db: Database session
        start_time: Optional start time for filtering
        end_time: Optional end time for filtering

    Returns:
        SuccessResponse containing PlayerDistributionResponse

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
    data = await service.get_player_distribution(
        start_time=start_time,
        end_time=end_time
    )

    return SuccessResponse(
        success=True,
        data=PlayerDistributionResponse(**data)
    )
