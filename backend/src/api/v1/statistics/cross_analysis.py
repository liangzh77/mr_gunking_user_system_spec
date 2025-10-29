"""多维度交叉分析API (T203)

提供灵活的多维度统计分析接口，支持按运营商/运营点/应用维度进行对比分析。
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID as PyUUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.dependencies import CurrentUserToken, DatabaseSession
from ....schemas.statistics.global_stats import CrossAnalysisResponse, DimensionType
from ....schemas.common import SuccessResponse
from ....services.global_statistics import GlobalStatisticsService
from ....core import get_token_subject
from ....core.exceptions import BadRequestException

router = APIRouter(tags=["Statistics"])


@router.get(
    "/cross-analysis",
    response_model=SuccessResponse[CrossAnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Cross-Dimensional Analysis",
    description="Get statistics with flexible dimension selection (admin only). Supports operator, site, and application dimensions for comparison.",
)
async def cross_analysis(
    token: CurrentUserToken,
    db: DatabaseSession,
    dimension: DimensionType = Query(
        ...,
        description="Analysis dimension: operator, site, or application",
        example="operator"
    ),
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
    dimension_values: Optional[str] = Query(
        None,
        description="Comma-separated list of dimension IDs to filter (e.g., 'uuid1,uuid2,uuid3')",
        example="550e8400-e29b-41d4-a716-446655440000,660e8400-e29b-41d4-a716-446655440001"
    ),
) -> SuccessResponse[CrossAnalysisResponse]:
    """Get multi-dimensional cross-analysis statistics.

    This endpoint provides flexible dimensional analysis:
    - Choose dimension: operator, site, or application
    - Optional time range filtering
    - Optional dimension value filtering (compare specific items)
    - Results sorted by revenue in descending order

    Use cases:
    - Compare performance across different operators
    - Analyze which sites generate the most revenue
    - Identify most popular applications
    - Filter to specific operators/sites/applications for detailed comparison

    Only accessible by admin users.

    Args:
        token: Admin JWT token
        db: Database session
        dimension: Analysis dimension (operator/site/application)
        start_time: Optional start time for filtering
        end_time: Optional end time for filtering
        dimension_values: Optional comma-separated list of UUIDs to filter

    Returns:
        SuccessResponse containing CrossAnalysisResponse

    Raises:
        401: Unauthorized (invalid or missing token)
        403: Forbidden (not an admin user)
        400: Bad Request (invalid parameters)
    """
    # Validate admin token
    admin_id = get_token_subject(token)

    # Validate time range
    if start_time and end_time and end_time < start_time:
        raise BadRequestException("end_time must be after start_time")

    # Parse dimension values if provided
    dimension_value_uuids = None
    if dimension_values:
        try:
            dimension_value_uuids = [
                PyUUID(vid.strip())
                for vid in dimension_values.split(",")
                if vid.strip()
            ]
        except ValueError as e:
            raise BadRequestException(f"Invalid UUID format in dimension_values: {str(e)}")

    # Validate dimension
    if dimension not in ["operator", "site", "application"]:
        raise BadRequestException(
            "Invalid dimension. Must be one of: operator, site, application",
            error_code="INVALID_DIMENSION"
        )

    # Get statistics
    service = GlobalStatisticsService(db)
    data = await service.get_cross_analysis(
        dimension=dimension.value if isinstance(dimension, DimensionType) else dimension,
        start_time=start_time,
        end_time=end_time,
        dimension_values=dimension_value_uuids
    )

    return SuccessResponse(
        success=True,
        data=CrossAnalysisResponse(**data)
    )
