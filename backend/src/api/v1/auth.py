"""授权API接口 (T046)

此模块定义游戏授权相关的API端点。

端点:
- POST /v1/auth/game/authorize - 游戏授权请求

认证方式:
- API Key认证 (X-API-Key header)
- HMAC签名验证 (X-Signature header)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...schemas.auth import (
    ErrorResponse,
    GameAuthorizeData,
    GameAuthorizeRequest,
    GameAuthorizeResponse,
)
from ...services.auth_service import AuthService
from ...services.billing_service import BillingService

router = APIRouter(prefix="/auth", tags=["授权"])


@router.post(
    "/game/authorize",
    response_model=GameAuthorizeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "请求参数错误(玩家数量超出范围、会话ID格式错误、时间戳过期等)"
        },
        401: {
            "model": ErrorResponse,
            "description": "认证失败(API Key无效)"
        },
        402: {
            "model": ErrorResponse,
            "description": "余额不足"
        },
        403: {
            "model": ErrorResponse,
            "description": "应用未授权或账户已锁定"
        },
        409: {
            "description": "会话重复(幂等性处理，返回已授权信息)"
        },
        429: {
            "model": ErrorResponse,
            "description": "请求频率超限"
        },
        500: {
            "model": ErrorResponse,
            "description": "服务器内部错误"
        }
    },
    summary="游戏授权请求",
    description="""
    头显Server请求游戏授权并扣费。

    **认证要求**:
    - X-API-Key: 运营商API Key (64位字符串)
    - X-Signature: HMAC-SHA256签名 (Base64编码)
    - X-Timestamp: Unix时间戳 (秒，5分钟有效)
    - X-Session-ID: 会话ID (格式: {operatorId}_{timestamp}_{random16})

    **业务逻辑**:
    1. 验证API Key有效性
    2. 验证HMAC签名 (防篡改)
    3. 验证时间戳 (防重放攻击)
    4. 验证会话ID格式和幂等性 (防重复扣费)
    5. 验证运营商对应用的授权状态
    6. 验证玩家数量在应用允许范围内
    7. 计算费用: 总费用 = 玩家数量 × 应用单人价格
    8. 检查账户余额是否充足
    9. 使用数据库事务扣费并创建使用记录
    10. 返回授权Token

    **幂等性**: 相同会话ID重复请求返回已授权信息，不重复扣费。
    """
)
async def authorize_game(
    request_body: GameAuthorizeRequest,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key", description="运营商API Key"),
    x_session_id: str = Header(..., alias="X-Session-ID", description="会话ID(幂等性标识)"),
    x_timestamp: int = Header(..., alias="X-Timestamp", description="Unix时间戳(秒)"),
    x_signature: str = Header(..., alias="X-Signature", description="HMAC-SHA256签名"),
    db: AsyncSession = Depends(get_db)
) -> GameAuthorizeResponse:
    """游戏授权API

    处理头显Server的游戏授权请求，完成验证、扣费、返回授权Token。

    Args:
        request_body: 请求体(app_id, site_id, player_count)
        request: FastAPI Request对象
        x_api_key: API Key (Header)
        x_session_id: 会话ID (Header)
        x_timestamp: 时间戳 (Header)
        x_signature: HMAC签名 (Header)
        db: 数据库会话

    Returns:
        GameAuthorizeResponse: 授权成功响应
    """
    # 初始化服务
    auth_service = AuthService(db)
    billing_service = BillingService(db)

    # ========== STEP 1: 验证API Key ==========
    operator = await auth_service.verify_operator_by_api_key(x_api_key)

    # ========== STEP 2: 验证会话ID格式 (FR-061) ==========
    await auth_service.verify_session_id_format(x_session_id, operator.id)

    # ========== STEP 3: 检查会话ID幂等性 ==========
    existing_record = await billing_service.check_session_idempotency(x_session_id)
    if existing_record:
        # 会话已存在,返回已授权信息(幂等性保护)
        return GameAuthorizeResponse(
            success=True,
            data=GameAuthorizeData(
                authorization_token=existing_record.authorization_token,
                session_id=existing_record.session_id,
                app_name=existing_record.application.app_name if existing_record.application else "未知应用",
                player_count=existing_record.player_count,
                unit_price=str(existing_record.price_per_player),
                total_cost=str(existing_record.total_cost),
                balance_after="0.00",  # 已授权记录不再查询余额
                authorized_at=existing_record.game_started_at
            )
        )

    # ========== STEP 4: 解析并验证请求参数 ==========
    try:
        app_id = UUID(request_body.app_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_APP_ID",
                "message": f"应用ID格式错误: {request_body.app_id}"
            }
        )

    try:
        site_id = UUID(request_body.site_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_SITE_ID",
                "message": f"运营点ID格式错误: {request_body.site_id}"
            }
        )

    # ========== STEP 5: 验证运营点归属 ==========
    site = await auth_service.verify_site_ownership(site_id, operator.id)

    # ========== STEP 6: 验证应用授权 ==========
    application, authorization = await auth_service.verify_application_authorization(
        app_id,
        operator.id
    )

    # ========== STEP 7: 验证玩家数量 ==========
    await auth_service.verify_player_count(request_body.player_count, application)

    # ========== STEP 8: 计算费用并检查余额 ==========
    total_cost = billing_service.calculate_total_cost(
        application.price_per_player,
        request_body.player_count
    )
    await billing_service.check_balance_sufficiency(operator, total_cost)

    # ========== STEP 9: 执行扣费事务 ==========
    client_ip = request.client.host if request.client else None

    usage_record, transaction_record, balance_after = await billing_service.create_authorization_transaction(
        session_id=x_session_id,
        operator_id=operator.id,
        site_id=site_id,
        application=application,
        player_count=request_body.player_count,
        client_ip=client_ip
    )

    # ========== STEP 10: 构造响应 ==========
    response_data = GameAuthorizeData(
        authorization_token=usage_record.authorization_token,
        session_id=usage_record.session_id,
        app_name=application.app_name,
        player_count=usage_record.player_count,
        unit_price=str(usage_record.price_per_player),
        total_cost=str(usage_record.total_cost),
        balance_after=str(balance_after),
        authorized_at=usage_record.game_started_at
    )

    return GameAuthorizeResponse(success=True, data=response_data)
