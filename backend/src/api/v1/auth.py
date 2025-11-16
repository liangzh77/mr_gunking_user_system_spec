"""授权API接口 (T046, T066, T067, T068)

此模块定义授权相关的API端点。

端点:
- POST /v1/auth/game/authorize - 游戏授权请求 (T046)
- POST /v1/auth/game/pre-authorize - 游戏预授权查询
- POST /v1/auth/operators/register - 运营商注册 (T066)
- POST /v1/auth/operators/login - 运营商登录 (T067)
- POST /v1/auth/operators/logout - 运营商登出 (T068)

认证方式:
- 游戏授权/预授权: Headset Token认证 (Authorization: Bearer {headset_token})
- 运营商注册/登录: 无需认证
- 运营商登出: JWT Token认证 (Authorization: Bearer {token})
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import require_operator, require_headset_token
from ...core import get_redis
from ...db.session import get_db
from ...schemas.auth import (
    ErrorResponse,
    GameAuthorizeData,
    GameAuthorizeRequest,
    GameAuthorizeResponse,
    GamePreAuthorizeData,
    GamePreAuthorizeResponse,
    GameSessionUploadRequest,
    GameSessionUploadResponse,
    HeadsetDeviceRecord,
    LoginResponse,
    OperatorLoginRequest,
)
from ...schemas.operator import (
    OperatorRegisterRequest,
    OperatorRegisterResponse,
)
from ...schemas.finance import FinanceLoginRequest
from ...services.auth_service import AuthService
from ...services.billing_service import BillingService
from ...services.operator import OperatorService

router = APIRouter(prefix="/auth", tags=["授权"])


@router.post(
    "/game/authorize",
    response_model=GameAuthorizeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "请求参数错误(玩家数量超出范围、会话ID格式错误等)"
        },
        401: {
            "model": ErrorResponse,
            "description": "认证失败(Headset Token无效或过期)"
        },
        402: {
            "model": ErrorResponse,
            "description": "余额不足"
        },
        403: {
            "model": ErrorResponse,
            "description": "应用未授权、账户已锁定、或使用了错误的Token类型(必须使用Headset Token，不能使用运营商登录Token)"
        },
        409: {
            "description": "会话重复(幂等性处理，返回已授权信息)"
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
    - Authorization: Bearer {headset_token} (24小时有效的Headset Token)

    **业务逻辑**:
    1. 验证Headset Token有效性
    2. 检查幂等性 (基于业务键: operator+app+site+player_count+时间窗口)
    3. 验证运营商对应用的授权状态
    4. 验证玩家数量在应用允许范围内
    5. 计算费用: 总费用 = 玩家数量 × 应用单人价格
    6. 检查账户余额是否充足
    7. 使用数据库事务扣费并创建使用记录
    8. 服务器生成唯一的session_id
    9. 返回授权Token和session_id

    **幂等性**: 30秒内相同的运营商、应用、运营点、玩家数量只允许授权一次。

    **session_id生成**: 服务器自动生成,格式为{operator_id}_{timestamp}_{random16}
    """
)
async def authorize_game(
    request_body: GameAuthorizeRequest,
    request: Request,
    token: dict = Depends(require_headset_token),
    db: AsyncSession = Depends(get_db)
) -> GameAuthorizeResponse:
    """游戏授权API

    处理头显Server的游戏授权请求，完成验证、扣费、返回授权Token。

    注意: session_id 由服务器自动生成,不需要客户端提供。

    Args:
        request_body: 请求体(app_code, site_id, player_count)
        request: FastAPI Request对象
        token: Headset Token payload (包含operator_id) - 必须使用Headset Token
        db: 数据库会话

    Returns:
        GameAuthorizeResponse: 授权成功响应,包含服务器生成的session_id
    """
    import asyncio

    # 初始化服务
    auth_service = AuthService(db)
    billing_service = BillingService(db)

    # ========== STEP 1: 从Token中提取operator_id并查询运营商 ==========
    operator_id = UUID(token["sub"])  # token["sub"]存储的是operator_id

    # 查询运营商对象（用于后续余额检查）
    from ...models.operator import OperatorAccount
    from sqlalchemy import select
    from sqlalchemy.orm import noload

    # 优化：禁用所有relationship加载，我们只需要balance字段
    stmt = select(OperatorAccount).where(
        OperatorAccount.id == operator_id,
        OperatorAccount.deleted_at.is_(None)
    ).options(noload('*'))
    result = await db.execute(stmt)
    operator = result.scalar_one_or_none()

    if not operator:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "OPERATOR_NOT_FOUND",
                "message": "运营商账户不存在或已删除"
            }
        )

    # ========== STEP 2: 解析并验证请求参数 ==========
    app_code = request_body.app_code

    # 处理site_id: 支持带"site_"前缀或纯UUID格式
    site_id_str = request_body.site_id
    if site_id_str.startswith("site_"):
        site_id_str = site_id_str[5:]  # 去掉"site_"前缀

    try:
        site_id = UUID(site_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_SITE_ID",
                "message": f"运营点ID格式错误: {request_body.site_id}"
            }
        )

    # ========== 优化: STEP 3-4 使用Redis缓存 + 合并SQL查询 ==========
    from ...core.cache import get_cache
    from ...services.cache_service import CacheService
    redis_cache = get_cache()
    cache_service = CacheService(redis_cache)

    # 尝试从缓存获取
    cached_app = await cache_service.get_application_by_code(app_code)
    cached_auth = await cache_service.get_authorization(operator_id, app_code)
    cached_site = await cache_service.get_site(site_id)

    if cached_app and cached_auth and cached_site:
        # 🎯 缓存全命中 - 直接使用缓存数据
        from ...models.application import Application
        from ...models.authorization import OperatorAppAuthorization
        from ...models.site import OperationSite
        from decimal import Decimal
        from datetime import datetime

        # 从缓存重建对象 (注意类型转换)
        application = Application(
            id=UUID(cached_app["id"]),
            app_code=cached_app["app_code"],
            app_name=cached_app["app_name"],
            price_per_player=Decimal(cached_app["price_per_player"]),
            min_players=cached_app["min_players"],
            max_players=cached_app["max_players"],
            is_active=cached_app["is_active"]
        )
        authorization = OperatorAppAuthorization(
            operator_id=UUID(cached_auth["operator_id"]),
            application_id=UUID(cached_auth["application_id"]),
            is_active=cached_auth["is_active"],
            expires_at=datetime.fromisoformat(cached_auth["expires_at"]) if cached_auth.get("expires_at") else None
        )
        site = OperationSite(
            id=UUID(cached_site["id"]),
            operator_id=UUID(cached_site["operator_id"]),
            name=cached_site["name"],
            is_active=cached_site["is_active"]
        )

        # 验证运营点归属
        if site.operator_id != operator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "SITE_NOT_OWNED",
                    "message": "该运营点不属于您，无权使用"
                }
            )

        # 验证运营点状态
        if not site.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "SITE_INACTIVE",
                    "message": "该运营点已停用，无法发起授权"
                }
            )

        # 验证应用状态
        if not application.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "APP_INACTIVE",
                    "message": f"应用 '{application.app_name}' 已下架，暂不可用"
                }
            )
    else:
        # ⚡ 缓存未命中 - 使用合并SQL查询
        operator_obj, site, application, authorization = await auth_service.verify_all_in_one_query(
            operator_id, site_id, app_code
        )

        # 异步写入缓存
        asyncio.create_task(cache_service.set_application(
            app_code,
            {
                "id": str(application.id),
                "app_code": application.app_code,
                "app_name": application.app_name,
                "price_per_player": str(application.price_per_player),
                "min_players": application.min_players,
                "max_players": application.max_players,
                "is_active": application.is_active
            },
            ttl=1800  # 30分钟
        ))
        asyncio.create_task(cache_service.set_authorization(
            operator_id,
            app_code,
            {
                "operator_id": str(authorization.operator_id),
                "application_id": str(authorization.application_id),
                "is_active": authorization.is_active,
                "expires_at": authorization.expires_at.isoformat() if authorization.expires_at else None
            },
            ttl=600  # 10分钟
        ))
        asyncio.create_task(cache_service.set_site(
            site_id,
            {
                "id": str(site.id),
                "operator_id": str(site.operator_id),
                "name": site.name,
                "is_active": site.is_active
            },
            ttl=1800  # 30分钟
        ))

    # ========== STEP 5: 验证玩家数量 ==========
    await auth_service.verify_player_count(request_body.player_count, application)

    # ========== STEP 6: 计算费用并检查余额 ==========
    total_cost = billing_service.calculate_total_cost(
        application.price_per_player,
        request_body.player_count
    )
    await billing_service.check_balance_sufficiency(operator, total_cost)

    # ========== STEP 7: 检查业务键幂等性 (30秒窗口) ==========
    from datetime import datetime, timedelta
    import hashlib

    # 构造业务键: operator_id + app_code + site_id + player_count
    business_key = f"{operator_id}_{app_code}_{site_id}_{request_body.player_count}"

    # 检查30秒内是否有相同业务键的授权记录
    time_window_start = datetime.utcnow() - timedelta(seconds=30)
    existing_record = await billing_service.check_recent_authorization(
        operator_id=operator_id,
        application_id=application.id,
        site_id=site_id,
        player_count=request_body.player_count,
        since=time_window_start
    )

    if existing_record:
        # 30秒内已有相同授权,返回已授权信息(幂等性保护)
        # 注意：数据库中所有金额字段都是以元为单位存储的，无需转换
        return GameAuthorizeResponse(
            success=True,
            data=GameAuthorizeData(
                session_id=existing_record.session_id,
                app_name=application.app_name,
                player_count=existing_record.player_count,
                unit_price=str(existing_record.price_per_player),
                total_cost=str(existing_record.total_cost),
                balance_after=str(operator.balance),  # 使用当前余额
                authorized_at=existing_record.game_started_at
            )
        )

    # ========== STEP 8: 生成唯一的session_id ==========
    import random
    import string
    import time as time_module

    timestamp_ms = int(time_module.time() * 1000)
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    session_id = f"{operator_id}_{timestamp_ms}_{random_str}"

    # ========== STEP 9: 执行扣费事务 ==========
    client_ip = request.client.host if request.client else None

    usage_record, transaction_record, balance_after = await billing_service.create_authorization_transaction(
        session_id=session_id,
        operator_id=operator_id,
        site_id=site_id,
        application=application,
        player_count=request_body.player_count,
        client_ip=client_ip,
        headset_ids=request_body.headset_ids
    )

    # ========== STEP 10: 构造响应 ==========
    response_data = GameAuthorizeData(
        session_id=usage_record.session_id,
        app_name=application.app_name,
        player_count=usage_record.player_count,
        unit_price=str(usage_record.price_per_player),
        total_cost=str(usage_record.total_cost),
        balance_after=str(balance_after),
        authorized_at=usage_record.game_started_at
    )

    return GameAuthorizeResponse(success=True, data=response_data)


@router.post(
    "/game/pre-authorize",
    response_model=GamePreAuthorizeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "请求参数错误"
        },
        401: {
            "model": ErrorResponse,
            "description": "认证失败(Token无效)"
        },
        402: {
            "model": ErrorResponse,
            "description": "余额不足"
        },
        403: {
            "model": ErrorResponse,
            "description": "应用未授权、账户已锁定、或使用了错误的Token类型(必须使用Headset Token，不能使用运营商登录Token)"
        },
        500: {
            "model": ErrorResponse,
            "description": "服务器内部错误"
        }
    },
    summary="游戏授权查询(预授权)",
    description="""
    查询游戏授权资格，不执行实际扣费操作。

    **认证要求**:
    - Authorization: Bearer {TOKEN} (由/operators/generate-headset-token生成的24小时TOKEN)

    **业务逻辑**:
    1. 验证Bearer Token有效性
    2. 验证运营商对应用的授权状态
    3. 验证玩家数量在应用允许范围内
    4. 计算费用
    5. 检查账户余额是否充足
    6. 返回授权资格信息(不扣费)
    """
)
async def pre_authorize_game(
    request_body: GameAuthorizeRequest,
    token: dict = Depends(require_headset_token),
    db: AsyncSession = Depends(get_db)
) -> GamePreAuthorizeResponse:
    """游戏授权查询API (预授权,不扣费) - 优化版 (Redis缓存 + 合并SQL)

    处理头显Server的游戏授权查询请求，验证资格但不执行扣费。

    性能优化:
    - 使用Redis缓存应用、授权、运营点信息 (TTL: 10-30分钟)
    - 使用合并SQL查询减少数据库往返 (3次 → 1次)
    - 运营商余额实时查询确保准确性

    Args:
        request_body: 请求体(app_id, site_id, player_count)
        token: Headset Token payload - 必须使用Headset Token
        db: 数据库会话

    Returns:
        GamePreAuthorizeResponse: 预授权响应
    """
    # 初始化服务
    auth_service = AuthService(db)
    billing_service = BillingService(db)

    # 初始化缓存服务
    from ...core.cache import get_cache
    from ...services.cache_service import CacheService
    redis_cache = get_cache()
    cache_service = CacheService(redis_cache)

    # ========== STEP 1: 从Token中提取operator_id并查询运营商 ==========
    operator_id = UUID(token.get("sub"))

    # 查询运营商对象（用于后续余额检查）
    from ...models.operator import OperatorAccount
    from sqlalchemy.orm import noload

    # 优化：禁用所有relationship加载
    stmt = select(OperatorAccount).where(
        OperatorAccount.id == operator_id,
        OperatorAccount.deleted_at.is_(None)
    ).options(noload('*'))
    result = await db.execute(stmt)
    operator = result.scalar_one_or_none()

    if not operator:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "OPERATOR_NOT_FOUND",
                "message": "运营商账户不存在或已删除"
            }
        )

    # ========== STEP 2: 解析并验证请求参数 ==========
    app_code = request_body.app_code

    # 处理site_id: 支持带"site_"前缀或纯UUID格式
    site_id_str = request_body.site_id
    if site_id_str.startswith("site_"):
        site_id_str = site_id_str[5:]  # 去掉"site_"前缀

    try:
        site_id = UUID(site_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_SITE_ID",
                "message": f"运营点ID格式错误: {request_body.site_id}"
            }
        )

    # ========== STEP 3-4: 尝试从缓存获取 (方案1: Redis缓存) ==========
    cached_app = await cache_service.get_application_by_code(app_code)
    cached_auth = await cache_service.get_authorization(operator_id, app_code)
    cached_site = await cache_service.get_site(site_id)

    if cached_app and cached_auth and cached_site:
        # 🎯 缓存全命中 - 直接使用缓存数据,无需查询数据库!
        from ...models.application import Application
        from ...models.authorization import OperatorAppAuthorization
        from ...models.site import OperationSite
        from decimal import Decimal
        from datetime import datetime

        # 从缓存重建对象 (注意类型转换: str -> UUID, str -> Decimal, str -> datetime)
        application = Application(
            id=UUID(cached_app["id"]),
            app_code=cached_app["app_code"],
            app_name=cached_app["app_name"],
            price_per_player=Decimal(cached_app["price_per_player"]),
            min_players=cached_app["min_players"],
            max_players=cached_app["max_players"],
            is_active=cached_app["is_active"]
        )
        authorization = OperatorAppAuthorization(
            operator_id=UUID(cached_auth["operator_id"]),
            application_id=UUID(cached_auth["application_id"]),
            is_active=cached_auth["is_active"],
            expires_at=datetime.fromisoformat(cached_auth["expires_at"]) if cached_auth.get("expires_at") else None
        )
        site = OperationSite(
            id=UUID(cached_site["id"]),
            operator_id=UUID(cached_site["operator_id"]),
            name=cached_site["name"],
            is_active=cached_site["is_active"]
        )

        # 验证运营点归属
        if site.operator_id != operator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "SITE_NOT_OWNED",
                    "message": "该运营点不属于您，无权使用"
                }
            )

        # 验证运营点状态
        if not site.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "SITE_INACTIVE",
                    "message": "该运营点已停用，无法发起授权"
                }
            )

        # 验证应用状态
        if not application.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "APP_INACTIVE",
                    "message": f"应用 '{application.app_name}' 已下架，暂不可用"
                }
            )

        # 验证授权是否过期
        from datetime import datetime
        if authorization.expires_at and authorization.expires_at < datetime.now(authorization.expires_at.tzinfo):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "AUTHORIZATION_EXPIRED",
                    "message": f"应用授权已过期"
                }
            )

    else:
        # ⚡ 缓存未命中 - 使用合并SQL查询 (方案2: 1条SQL替代3条)
        operator, site, application, authorization = await auth_service.verify_all_in_one_query(
            operator_id, site_id, app_code
        )

        # 缓存查询结果 (异步写入,不阻塞主流程)
        import asyncio
        asyncio.create_task(cache_service.set_application(
            app_code,
            {
                "id": str(application.id),
                "app_code": application.app_code,
                "app_name": application.app_name,
                "price_per_player": str(application.price_per_player),
                "min_players": application.min_players,
                "max_players": application.max_players,
                "is_active": application.is_active
            },
            ttl=1800  # 30分钟
        ))
        asyncio.create_task(cache_service.set_authorization(
            operator_id,
            app_code,
            {
                "operator_id": str(authorization.operator_id),
                "application_id": str(authorization.application_id),
                "is_active": authorization.is_active,
                "expires_at": authorization.expires_at.isoformat() if authorization.expires_at else None
            },
            ttl=600  # 10分钟
        ))
        asyncio.create_task(cache_service.set_site(
            site_id,
            {
                "id": str(site.id),
                "operator_id": str(site.operator_id),
                "name": site.name,
                "is_active": site.is_active
            },
            ttl=1800  # 30分钟
        ))

    # ========== STEP 5: 验证玩家数量 ==========
    await auth_service.verify_player_count(request_body.player_count, application)

    # ========== STEP 6: 计算费用 ==========
    total_cost = billing_service.calculate_total_cost(
        application.price_per_player,
        request_body.player_count
    )

    # ========== STEP 7: 检查余额 (不扣费) ==========
    can_authorize = True
    try:
        await billing_service.check_balance_sufficiency(operator, total_cost)
    except HTTPException:
        can_authorize = False

    # ========== STEP 8: 构造响应 ==========
    # 注意：数据库中所有金额字段都是以元为单位存储的，无需转换
    response_data = GamePreAuthorizeData(
        can_authorize=can_authorize,
        app_code=application.app_code,
        app_name=application.app_name,
        player_count=request_body.player_count,
        unit_price=str(application.price_per_player),
        total_cost=str(total_cost),
        current_balance=str(operator.balance)
    )

    return GamePreAuthorizeResponse(success=True, data=response_data)


@router.post(
    "/game/session/upload",
    response_model=GameSessionUploadResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "请求参数错误"
        },
        401: {
            "model": ErrorResponse,
            "description": "认证失败(Token无效)"
        },
        404: {
            "model": ErrorResponse,
            "description": "会话不存在"
        },
        500: {
            "model": ErrorResponse,
            "description": "服务器内部错误"
        }
    },
    summary="上传游戏Session信息",
    description="""
    上传游戏Session的详细信息，包括游戏时间、过程信息和头显设备记录。

    **认证要求**:
    - Authorization: Bearer {TOKEN}

    **业务逻辑**:
    1. 验证Bearer Token有效性
    2. 根据session_id查找授权记录
    3. 创建游戏Session记录
    4. 为每个头显设备创建记录（自动注册新设备）
    """
)
async def upload_game_session(
    request_body: GameSessionUploadRequest,
    token: dict = Depends(require_headset_token),
    db: AsyncSession = Depends(get_db)
) -> GameSessionUploadResponse:
    """上传游戏Session信息API

    处理头显Server的游戏Session数据上传请求。

    Args:
        request_body: 请求体(session_id, start_time, end_time, process_info, headset_devices)
        token: Headset Token payload - 必须使用Headset Token
        db: 数据库会话

    Returns:
        GameSessionUploadResponse: 上传响应
    """
    from uuid import UUID as PyUUID
    from ...models.usage_record import UsageRecord
    from ...models.game_session import GameSession
    from ...models.headset_device import HeadsetDevice
    from ...models.headset_game_record import HeadsetGameRecord

    try:
        # ========== STEP 1: 查找授权记录 ==========
        stmt = select(UsageRecord).where(UsageRecord.session_id == request_body.session_id)
        result = await db.execute(stmt)
        usage_record = result.scalar_one_or_none()

        if not usage_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "SESSION_NOT_FOUND",
                    "message": f"会话不存在: {request_body.session_id}"
                }
            )

        # 验证session归属
        operator_id = token.get("sub")
        if str(usage_record.operator_id) != operator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "SESSION_ACCESS_DENIED",
                    "message": "无权访问此会话"
                }
            )

        # ========== STEP 2: 批量删除旧的游戏Session记录(覆盖模式) ==========
        # 🚀 优化: 使用批量DELETE替代循环删除，利用CASCADE自动删除子记录
        # 由于HeadsetGameRecord配置了ondelete="CASCADE"，删除GameSession时会自动级联删除关联记录
        from sqlalchemy import delete

        await db.execute(
            delete(GameSession).where(GameSession.usage_record_id == usage_record.id)
        )
        # 注意: 不需要flush，批量DELETE已经立即执行

        # 创建新的游戏Session记录
        game_session = GameSession(
            usage_record_id=usage_record.id,
            start_time=request_body.start_time,
            end_time=request_body.end_time,
            process_info=request_body.process_info
        )
        db.add(game_session)
        await db.flush()  # 获取game_session.id

        # ========== STEP 3: 批量处理头显设备记录 ==========
        if request_body.headset_devices:
            # 🚀 优化: 批量查询所有设备，避免N次数据库查询
            device_ids = [d.device_id for d in request_body.headset_devices]
            stmt = select(HeadsetDevice).where(HeadsetDevice.device_id.in_(device_ids))
            result = await db.execute(stmt)
            existing_devices = {d.device_id: d for d in result.scalars().all()}

            # 收集需要创建的新设备和游戏记录
            new_devices = []
            game_records_to_add = []

            for device_record in request_body.headset_devices:
                headset_device = existing_devices.get(device_record.device_id)

                if not headset_device:
                    # 创建新设备对象
                    headset_device = HeadsetDevice(
                        device_id=device_record.device_id,
                        site_id=usage_record.site_id,
                        device_name=device_record.device_name,
                        first_used_at=device_record.start_time or datetime.utcnow(),
                        last_used_at=device_record.end_time or datetime.utcnow()
                    )
                    new_devices.append(headset_device)
                    # 添加到字典，后续创建游戏记录时使用
                    existing_devices[device_record.device_id] = headset_device
                else:
                    # 更新现有设备信息
                    if device_record.device_name:
                        headset_device.device_name = device_record.device_name

                    # 更新最后使用时间
                    if device_record.end_time:
                        headset_device.last_used_at = device_record.end_time
                    else:
                        headset_device.last_used_at = datetime.utcnow()

            # 🚀 优化: 批量插入新设备
            if new_devices:
                db.add_all(new_devices)
                await db.flush()  # 必须flush以获取新设备的ID

            # 🚀 优化: 批量创建游戏记录
            for device_record in request_body.headset_devices:
                headset_device = existing_devices[device_record.device_id]
                game_records_to_add.append(
                    HeadsetGameRecord(
                        game_session_id=game_session.id,
                        headset_device_id=headset_device.id,
                        start_time=device_record.start_time,
                        end_time=device_record.end_time,
                        process_info=device_record.process_info
                    )
                )

            # 批量添加游戏记录
            if game_records_to_add:
                db.add_all(game_records_to_add)

        # ========== STEP 4: 提交事务 ==========
        await db.commit()

        return GameSessionUploadResponse(
            success=True,
            message="游戏信息上传成功"
        )

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "UPLOAD_FAILED",
                "message": f"上传游戏信息失败: {str(e)}"
            }
        )


# ==================== 运营商注册和登录 (User Story 2) ====================


@router.post(
    "/operators/register",
    response_model=OperatorRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "请求参数错误(用户名已存在、密码强度不足、手机号格式错误等)"
        },
        500: {
            "model": ErrorResponse,
            "description": "服务器内部错误"
        }
    },
    summary="运营商注册",
    description="""
    创建新的运营商账户。

    **请求参数**:
    - username: 用户名(3-20字符,仅字母数字下划线,唯一)
    - password: 密码(8-32字符,必须包含大小写字母和数字)
    - name: 真实姓名或公司名(2-50字符)
    - phone: 联系电话(11位中国手机号)
    - email: 邮箱地址

    **响应数据**:
    - operator_id: 运营商ID (格式: op_{uuid})
    - username: 用户名
    - api_key: API Key (64位十六进制字符串,**仅显示一次,请妥善保存**)
    - category: 客户分类(新注册默认为trial)
    - balance: 账户余额(初始为0.00元)
    - created_at: 创建时间

    **安全特性**:
    - 密码使用bcrypt哈希存储
    - API Key使用密码学安全随机数生成(secrets模块)
    - 用户名唯一性验证
    """
)
async def register_operator(
    request: OperatorRegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> OperatorRegisterResponse:
    """运营商注册API (T066)

    处理运营商注册请求,创建账户并生成API Key。

    Args:
        request: 注册请求数据(包含username, password, name, phone, email, sms_key, sms_code)
        db: 数据库会话
        redis: Redis连接

    Returns:
        OperatorRegisterResponse: 注册成功响应(包含operator_id和api_key)

    Raises:
        HTTPException 400: 参数错误(用户名已存在、密码不符合要求等)
        HTTPException 401: 短信验证码错误
        HTTPException 500: 服务器内部错误
    """
    # 验证短信验证码
    from .common import verify_sms_code
    is_sms_valid = await verify_sms_code(
        request.sms_key,
        request.sms_code,
        request.phone,
        redis
    )

    if not is_sms_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_SMS_CODE",
                "message": "短信验证码错误或已过期"
            }
        )

    operator_service = OperatorService(db)

    try:
        # 调用服务层创建运营商账户
        data = await operator_service.register(request)

        # 包装响应格式
        from ...schemas.operator import OperatorRegisterResponse
        return OperatorRegisterResponse(
            success=True,
            message="注册成功",
            data=data
        )

    except HTTPException:
        # 重新抛出业务逻辑异常(如用户名已存在)
        raise

    except Exception as e:
        # 捕获未预期的错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"注册失败: {str(e)}"
            }
        )


@router.post(
    "/operators/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "请求参数错误(缺少必填字段或字段为空)"
        },
        401: {
            "model": ErrorResponse,
            "description": "认证失败(用户名或密码错误)"
        },
        403: {
            "model": ErrorResponse,
            "description": "账户已注销或被锁定"
        },
        500: {
            "model": ErrorResponse,
            "description": "服务器内部错误"
        }
    },
    summary="运营商登录",
    description="""
    运营商账户登录。

    **请求参数**:
    - username: 用户名(必填)
    - password: 密码(必填)

    **响应数据**:
    - success: 请求是否成功(true)
    - data.access_token: JWT Token (用于后续API认证)
    - data.token_type: Token类型(Bearer)
    - data.expires_in: Token有效期(秒,30天=2592000秒)
    - data.operator: 运营商基本信息
        - operator_id: 运营商ID
        - username: 用户名
        - name: 真实姓名或公司名
        - category: 客户分类(trial/normal/vip)

    **使用JWT Token**:
    在后续请求中,在Header中添加:
    ```
    Authorization: Bearer {access_token}
    ```

    **安全特性**:
    - 密码使用bcrypt验证
    - JWT Token有效期30天
    - 更新最近登录时间和IP
    - 检查账户状态(是否注销/锁定)
    """
)
async def login_operator(
    request: OperatorLoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
) -> LoginResponse:
    """运营商登录API (T067)

    处理运营商登录请求,验证凭证并返回JWT Token。

    Args:
        request: 登录请求数据(包含username, password, captcha_key, captcha_code)
        http_request: FastAPI Request对象(用于获取客户端IP)
        db: 数据库会话
        redis: Redis连接

    Returns:
        LoginResponse: 登录成功响应(包含access_token和operator信息)

    Raises:
        HTTPException 400: 参数错误(缺少必填字段)
        HTTPException 401: 认证失败(用户名或密码错误、验证码错误)
        HTTPException 403: 账户已注销或被锁定
        HTTPException 500: 服务器内部错误
    """
    # 验证验证码
    from .common import verify_captcha
    is_captcha_valid = await verify_captcha(
        request.captcha_key,
        request.captcha_code,
        redis
    )

    if not is_captcha_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_CAPTCHA",
                "message": "验证码错误或已过期"
            }
        )

    operator_service = OperatorService(db)

    try:
        # 获取客户端IP
        client_ip = http_request.client.host if http_request.client else None

        # 调用服务层进行登录
        response = await operator_service.login(
            username=request.username,
            password=request.password,
            login_ip=client_ip
        )

        return response

    except HTTPException:
        # 重新抛出业务逻辑异常(如认证失败、账户锁定等)
        raise

    except Exception as e:
        # 捕获未预期的错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"登录失败: {str(e)}"
            }
        )


@router.post(
    "/operators/logout",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "未认证或Token无效"
        },
        500: {
            "model": ErrorResponse,
            "description": "服务器内部错误"
        }
    },
    summary="运营商登出",
    description="""
    运营商退出登录。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}

    **实现说明**:
    本API采用客户端清理Token策略,服务端只验证Token有效性:
    - 客户端收到200响应后应立即清除本地存储的Token
    - Token在有效期内仍可使用(无服务端黑名单)
    - 建议客户端配合实现Token主动清理和过期检查

    **Token黑名单支持**:
    如需实现服务端Token黑名单(防止登出后Token仍可使用):
    - 可集成Redis存储已登出的Token
    - 在JWT中间件添加黑名单检查逻辑
    - 当前实现为轻量级方案,适用于小规模部署

    **响应数据**:
    - success: 请求是否成功(true)
    - message: "已退出登录"
    """
)
async def logout_operator(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """运营商登出API (T068)

    处理运营商登出请求。

    当前实现策略:
    - 验证Token有效性(通过require_operator依赖注入)
    - 返回成功响应
    - 依赖客户端清理本地Token
    - 无服务端Token黑名单(简化实现)

    扩展方向:
    - 如需实现Token黑名单,可在此添加Redis逻辑
    - 将token["jti"]或完整token加入Redis黑名单
    - 设置过期时间与Token有效期一致

    Args:
        token: JWT Token payload (通过require_operator解析)
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "message": "已退出登录"
        }

    Raises:
        HTTPException 401: Token无效或已过期
        HTTPException 500: 服务器内部错误
    """
    try:
        # 可选: 在此处添加Token黑名单逻辑
        # 例如: await add_token_to_blacklist(token["jti"], expires_in=2592000)

        # 返回成功响应
        return {
            "success": True,
            "message": "已退出登录"
        }

    except Exception as e:
        # 捕获未预期的错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"登出失败: {str(e)}"
            }
        )


# ==================== 财务人员登录 (T162) ====================


@router.post(
    "/finance/login",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "请求参数错误(缺少必填字段或字段为空)"
        },
        401: {
            "model": ErrorResponse,
            "description": "认证失败(用户名或密码错误,或账号已禁用)"
        },
        500: {
            "model": ErrorResponse,
            "description": "服务器内部错误"
        }
    },
    summary="财务人员登录",
    description="""
    财务人员账户登录。

    **请求参数**:
    - username: 用户名(必填)
    - password: 密码(必填)

    **响应数据**:
    - access_token: JWT Token (用于后续API认证)
    - token_type: Token类型(Bearer)
    - expires_in: Token有效期(秒,24小时=86400秒)
    - finance: 财务人员基本信息
        - finance_id: 财务人员ID
        - username: 用户名
        - full_name: 真实姓名
        - role: 角色(specialist/manager/auditor)
        - email: 邮箱地址

    **使用JWT Token**:
    在后续请求中,在Header中添加:
    ```
    Authorization: Bearer {access_token}
    ```

    **安全特性**:
    - 密码使用bcrypt验证
    - JWT Token有效期24小时
    - 更新最近登录时间和IP
    - 检查账户状态(是否禁用)
    """
)
async def login_finance(
    login_request: FinanceLoginRequest,
    http_request: Request = None,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
) -> dict:
    """财务人员登录API (T162)

    处理财务人员登录请求,验证凭证并返回JWT Token。

    Args:
        login_request: 登录请求数据(包含username, password, captcha_key, captcha_code)
        http_request: FastAPI Request对象(用于获取客户端IP)
        db: 数据库会话
        redis: Redis连接

    Returns:
        dict: 登录成功响应(包含access_token和finance信息)

    Raises:
        HTTPException 400: 参数错误(缺少必填字段)
        HTTPException 401: 认证失败(用户名或密码错误、验证码错误)
        HTTPException 500: 服务器内部错误
    """
    from ...services.finance_service import FinanceService

    try:

        # 验证验证码
        from .common import verify_captcha
        is_captcha_valid = await verify_captcha(
            login_request.captcha_key,
            login_request.captcha_code,
            redis
        )

        if not is_captcha_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "INVALID_CAPTCHA",
                    "message": "验证码错误或已过期"
                }
            )

        # 获取客户端IP
        client_ip = http_request.client.host if http_request.client else None

        # 调用财务服务进行登录
        finance_service = FinanceService(db)
        response = await finance_service.login(
            username=login_request.username,
            password=login_request.password,
            ip_address=client_ip
        )

        # 返回直接字段格式(符合contract tests期望)
        return {
            "access_token": response.access_token,
            "token_type": response.token_type,
            "expires_in": response.expires_in,
            "finance": {
                "finance_id": response.finance.finance_id,
                "username": response.finance.username,
                "name": response.finance.full_name,
                "full_name": response.finance.full_name,
                "role": "finance",  # 统一返回"finance"角色
                "email": response.finance.email
            }
        }

    except Exception as e:
        # 捕获所有异常，检查异常类型
        error_msg = str(e)

        # 检查是否为认证失败异常
        if "用户名或密码错误" in error_msg or "Invalid credentials" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "INVALID_CREDENTIALS",
                    "message": "用户名或密码错误"
                }
            )

        # 检查是否为验证错误
        if "validation error" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error_code": "VALIDATION_ERROR",
                    "message": "请求参数验证失败"
                }
            )

        # 其他错误返回500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"登录失败: {error_msg}"
            }
        )
