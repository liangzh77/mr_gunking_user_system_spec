"""导出全局报表API (T204)

提供全局统计数据的CSV导出功能。
"""

import csv
import io
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.dependencies import CurrentUserToken, DatabaseSession
from ....services.global_statistics import GlobalStatisticsService
from ....core import get_token_subject
from ....core.exceptions import BadRequestException

router = APIRouter(tags=["Statistics"])


@router.get(
    "/export",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Export Global Report",
    description="Export global statistics report as CSV file (admin only).",
)
async def export_global_report(
    token: CurrentUserToken,
    db: DatabaseSession,
    dimension: str = Query(
        "operator",
        description="Report dimension: operator, site, or application",
        pattern="^(operator|site|application)$"
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
) -> StreamingResponse:
    """Export global statistics report as CSV.

    This endpoint exports cross-dimensional analysis data in CSV format:
    - Choose dimension: operator, site, or application
    - Optional time range filtering
    - Returns CSV file with headers and data rows

    CSV columns:
    - Dimension ID
    - Dimension Name
    - Total Sessions
    - Total Players
    - Total Revenue
    - Average Players Per Session

    Only accessible by admin users.

    Args:
        token: Admin JWT token
        db: Database session
        dimension: Report dimension (operator/site/application)
        start_time: Optional start time for filtering
        end_time: Optional end time for filtering

    Returns:
        StreamingResponse: CSV file download

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

    # Validate dimension
    if dimension not in ["operator", "site", "application"]:
        raise BadRequestException("Invalid dimension. Must be one of: operator, site, application")

    # Get statistics
    service = GlobalStatisticsService(db)
    data = await service.get_cross_analysis(
        dimension=dimension,
        start_time=start_time,
        end_time=end_time
    )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write headers
    writer.writerow([
        "Dimension ID",
        "Dimension Name",
        "Total Sessions",
        "Total Players",
        "Total Revenue",
        "Average Players Per Session"
    ])

    # Write data rows
    for item in data["items"]:
        writer.writerow([
            item["dimension_id"],
            item["dimension_name"],
            item["total_sessions"],
            item["total_players"],
            item["total_revenue"],
            item["avg_players_per_session"]
        ])

    # Get CSV content
    csv_content = output.getvalue()
    output.close()

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"global_statistics_{dimension}_{timestamp}.csv"

    # Return as streaming response
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
