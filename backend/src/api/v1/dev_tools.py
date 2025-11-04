"""Development tools API endpoints.

SECURITY WARNING: These endpoints should ONLY be available in development environment!
Never expose these endpoints in production.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_db, require_operator
from ...core import create_headset_token, get_logger, get_settings
from ...models.operator import OperatorAccount
from ...models.application import Application
from ...models.site import OperationSite

logger = get_logger(__name__)
router = APIRouter()


class HeadsetTokenRequest(BaseModel):
    """Request body for generating test headset token."""

    operator_id: str = Field(
        description="运营商ID (可以是你登录后从 /api/v1/operators/profile 获取)"
    )
    application_id: str = Field(
        description="应用ID (可以从 /api/v1/operators/applications 获取)"
    )
    site_id: str = Field(
        description="运营点ID (可以从 /api/v1/operators/sites 获取)"
    )


class HeadsetTokenResponse(BaseModel):
    """Response for headset token generation."""

    headset_token: str = Field(description="生成的Headset Token (24小时有效)")
    expires_in: int = Field(description="有效期（秒）", default=86400)
    operator_id: str = Field(description="运营商ID")
    application_id: str = Field(description="应用ID")
    site_id: str = Field(description="运营点ID")
    usage_example: dict[str, Any] = Field(description="使用示例")


@router.post(
    "/generate-headset-token",
    response_model=HeadsetTokenResponse,
    summary="[开发专用] 生成测试用Headset Token",
    description="""
    **仅供开发测试使用！生产环境不应启用此接口！**

    生成一个Headset Token用于测试头显Server API接口。

    ### 使用步骤：
    1. 使用运营商账号登录获取login token
    2. 调用此接口生成headset token
    3. 在Swagger UI中使用生成的headset token测试头显Server API

    ### 参数获取：
    - `operator_id`: 从 GET /api/v1/operators/profile 获取
    - `application_id`: 从 GET /api/v1/operators/applications 获取
    - `site_id`: 从 GET /api/v1/operators/sites 获取

    ### 注意事项：
    - 此token只能用于测试，不应在实际应用中使用
    - Headset Token有效期为24小时
    - 确保提供的operator_id、application_id、site_id都是存在且有效的
    """,
    tags=["开发工具"],
)
async def generate_headset_token(
    request_body: HeadsetTokenRequest,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
) -> HeadsetTokenResponse:
    """Generate a test headset token for API testing.

    Args:
        request_body: Token generation request
        token: Current operator token (from login)
        db: Database session

    Returns:
        HeadsetTokenResponse with generated token

    Raises:
        HTTPException: If not in development environment or validation fails
    """
    # 1. Check environment - ONLY allow in development
    settings = get_settings()
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "NOT_AVAILABLE_IN_PRODUCTION",
                "message": "此接口仅在开发环境可用，生产环境已禁用"
            }
        )

    # Normalize IDs: Remove prefixes if present
    # application_id: 支持 "app_" 前缀或纯UUID
    application_id_str = request_body.application_id
    if application_id_str.startswith("app_"):
        application_id_str = application_id_str[4:]  # 去掉"app_"前缀

    # site_id: 支持 "site_" 前缀或纯UUID
    site_id_str = request_body.site_id
    if site_id_str.startswith("site_"):
        site_id_str = site_id_str[5:]  # 去掉"site_"前缀

    logger.info(
        "dev_tool_generate_token",
        operator_id=request_body.operator_id,
        application_id=application_id_str,
        site_id=site_id_str,
        requester=token.get("sub")
    )

    # 2. Validate operator exists
    operator_stmt = select(OperatorAccount).where(OperatorAccount.id == request_body.operator_id)
    operator_result = await db.execute(operator_stmt)
    operator = operator_result.scalar_one_or_none()

    if not operator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "OPERATOR_NOT_FOUND",
                "message": f"运营商 {request_body.operator_id} 不存在"
            }
        )

    # 3. Validate application exists (use normalized ID)
    app_stmt = select(Application).where(Application.id == application_id_str)
    app_result = await db.execute(app_stmt)
    application = app_result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "APPLICATION_NOT_FOUND",
                "message": f"应用 {request_body.application_id} 不存在"
            }
        )

    # 4. Validate site exists and belongs to operator (use normalized ID)
    site_stmt = select(OperationSite).where(
        OperationSite.id == site_id_str,
        OperationSite.operator_id == request_body.operator_id
    )
    site_result = await db.execute(site_stmt)
    site = site_result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SITE_NOT_FOUND",
                "message": f"运营点 {request_body.site_id} 不存在或不属于运营商 {request_body.operator_id}"
            }
        )

    # 5. Generate headset token
    headset_token = create_headset_token(
        operator_id=request_body.operator_id,
        operator_username=operator.username,
    )

    # 6. Return token with usage example
    return HeadsetTokenResponse(
        headset_token=headset_token,
        expires_in=86400,  # 24 hours
        operator_id=request_body.operator_id,
        application_id=request_body.application_id,
        site_id=request_body.site_id,
        usage_example={
            "description": "在Swagger UI中使用此token",
            "steps": [
                "1. 点击页面右上角的 'Authorize' 按钮",
                "2. 在弹出框中输入: Bearer {headset_token}",
                "3. 点击 'Authorize' 完成认证",
                "4. 现在可以测试头显Server API了"
            ],
            "test_endpoints": [
                "POST /api/v1/auth/game/pre-authorize - 预授权",
                "POST /api/v1/auth/game/authorize - 授权",
                "POST /api/v1/auth/game/session - 上传会话数据"
            ]
        }
    )
