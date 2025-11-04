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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import require_operator
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
            "description": "应用未授权或账户已锁定"
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
    - X-Session-ID: 会话ID (格式: {operatorId}_{timestamp}_{random16})

    **业务逻辑**:
    1. 验证Headset Token有效性
    2. 验证会话ID格式和幂等性 (防重复扣费)
    3. 验证运营商对应用的授权状态
    4. 验证玩家数量在应用允许范围内
    5. 计算费用: 总费用 = 玩家数量 × 应用单人价格
    6. 检查账户余额是否充足
    7. 使用数据库事务扣费并创建使用记录
    8. 返回授权Token

    **幂等性**: 相同会话ID重复请求返回已授权信息，不重复扣费。
    """
)
async def authorize_game(
    request_body: GameAuthorizeRequest,
    request: Request,
    x_session_id: str = Header(..., alias="X-Session-ID", description="会话ID(幂等性标识)"),
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> GameAuthorizeResponse:
    """游戏授权API

    处理头显Server的游戏授权请求，完成验证、扣费、返回授权Token。

    Args:
        request_body: 请求体(app_code, site_id, player_count)
        request: FastAPI Request对象
        x_session_id: 会话ID (Header)
        token: Headset Token payload (包含operator_id)
        db: 数据库会话

    Returns:
        GameAuthorizeResponse: 授权成功响应
    """
    # 初始化服务
    auth_service = AuthService(db)
    billing_service = BillingService(db)

    # ========== STEP 1: 从Token中提取operator_id并查询运营商 ==========
    operator_id = UUID(token["sub"])  # token["sub"]存储的是operator_id

    # 查询运营商对象（用于后续余额检查）
    from ...models.operator import OperatorAccount
    from sqlalchemy import select

    stmt = select(OperatorAccount).where(
        OperatorAccount.id == operator_id,
        OperatorAccount.deleted_at.is_(None)
    )
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

    # ========== STEP 2: 验证会话ID格式 (FR-061) ==========
    await auth_service.verify_session_id_format(x_session_id, operator_id)

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

    # ========== STEP 5: 验证运营点归属 ==========
    site = await auth_service.verify_site_ownership(site_id, operator_id)

    # ========== STEP 6: 通过app_code查询应用并验证授权 ==========
    application, authorization = await auth_service.verify_application_authorization_by_code(
        app_code,
        operator_id
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
        operator_id=operator_id,
        site_id=site_id,
        application=application,
        player_count=request_body.player_count,
        client_ip=client_ip,
        headset_ids=request_body.headset_ids
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
            "description": "应用未授权或账户已锁定"
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
    - Authorization: Bearer {TOKEN} (由/operators/generate-token生成的24小时TOKEN)

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
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> GamePreAuthorizeResponse:
    """游戏授权查询API (预授权,不扣费)

    处理头显Server的游戏授权查询请求，验证资格但不执行扣费。

    Args:
        request_body: 请求体(app_id, site_id, player_count)
        token: Bearer Token payload (由require_operator验证)
        db: 数据库会话

    Returns:
        GamePreAuthorizeResponse: 预授权响应
    """
    # 初始化服务
    auth_service = AuthService(db)
    billing_service = BillingService(db)

    # ========== STEP 1: 从Token中提取operator_id并查询运营商 ==========
    operator_id = UUID(token.get("sub"))

    # 查询运营商对象（用于后续余额检查）
    from ...models.operator import OperatorAccount

    stmt = select(OperatorAccount).where(
        OperatorAccount.id == operator_id,
        OperatorAccount.deleted_at.is_(None)
    )
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

    # ========== STEP 3: 验证运营点归属 ==========
    site = await auth_service.verify_site_ownership(site_id, operator_id)

    # ========== STEP 4: 通过app_code验证应用授权 ==========
    application, authorization = await auth_service.verify_application_authorization_by_code(
        app_code,
        operator_id
    )

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
    from ...core.utils import cents_to_yuan
    response_data = GamePreAuthorizeData(
        can_authorize=can_authorize,
        app_code=application.app_code,
        app_name=application.app_name,
        player_count=request_body.player_count,
        unit_price=str(cents_to_yuan(application.price_per_player)),
        total_cost=str(cents_to_yuan(total_cost)),
        current_balance=str(cents_to_yuan(operator.balance))
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
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> GameSessionUploadResponse:
    """上传游戏Session信息API

    处理头显Server的游戏Session数据上传请求。

    Args:
        request_body: 请求体(session_id, start_time, end_time, process_info, headset_devices)
        token: Bearer Token payload
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

        # ========== STEP 2: 创建游戏Session记录 ==========
        game_session = GameSession(
            usage_record_id=usage_record.id,
            start_time=request_body.start_time,
            end_time=request_body.end_time,
            process_info=request_body.process_info
        )
        db.add(game_session)
        await db.flush()  # 获取game_session.id

        # ========== STEP 3: 处理头显设备记录 ==========
        if request_body.headset_devices:
            for device_record in request_body.headset_devices:
                # 查找或创建头显设备
                stmt = select(HeadsetDevice).where(
                    HeadsetDevice.device_id == device_record.device_id,
                    HeadsetDevice.site_id == usage_record.site_id
                )
                result = await db.execute(stmt)
                headset_device = result.scalar_one_or_none()

                if not headset_device:
                    # 创建新设备
                    headset_device = HeadsetDevice(
                        device_id=device_record.device_id,
                        site_id=usage_record.site_id,
                        device_name=device_record.device_name,
                        first_used_at=device_record.start_time or datetime.utcnow(),
                        last_used_at=device_record.end_time or datetime.utcnow()
                    )
                    db.add(headset_device)
                    await db.flush()
                else:
                    # 更新最后使用时间
                    if device_record.end_time:
                        headset_device.last_used_at = device_record.end_time
                    else:
                        headset_device.last_used_at = datetime.utcnow()

                # 创建头显游戏记录
                headset_game_record = HeadsetGameRecord(
                    game_session_id=game_session.id,
                    headset_device_id=headset_device.id,
                    start_time=device_record.start_time,
                    end_time=device_record.end_time,
                    process_info=device_record.process_info
                )
                db.add(headset_game_record)

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
    db: AsyncSession = Depends(get_db)
) -> OperatorRegisterResponse:
    """运营商注册API (T066)

    处理运营商注册请求,创建账户并生成API Key。

    Args:
        request: 注册请求数据(包含username, password, name, phone, email)
        db: 数据库会话

    Returns:
        OperatorRegisterResponse: 注册成功响应(包含operator_id和api_key)

    Raises:
        HTTPException 400: 参数错误(用户名已存在、密码不符合要求等)
        HTTPException 500: 服务器内部错误
    """
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
    db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """运营商登录API (T067)

    处理运营商登录请求,验证凭证并返回JWT Token。

    Args:
        request: 登录请求数据(包含username, password)
        http_request: FastAPI Request对象(用于获取客户端IP)
        db: 数据库会话

    Returns:
        LoginResponse: 登录成功响应(包含access_token和operator信息)

    Raises:
        HTTPException 400: 参数错误(缺少必填字段)
        HTTPException 401: 认证失败(用户名或密码错误)
        HTTPException 403: 账户已注销或被锁定
        HTTPException 500: 服务器内部错误
    """
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
    request_data: dict = Body(...),
    http_request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """财务人员登录API (T162)

    处理财务人员登录请求,验证凭证并返回JWT Token。

    Args:
        request_data: 登录请求数据(包含username, password)
        http_request: FastAPI Request对象(用于获取客户端IP)
        db: 数据库会话

    Returns:
        dict: 登录成功响应(包含access_token和finance信息)

    Raises:
        HTTPException 400: 参数错误(缺少必填字段)
        HTTPException 401: 认证失败(用户名或密码错误)
        HTTPException 500: 服务器内部错误
    """
    from ...services.finance_service import FinanceService
    from ...schemas.finance import FinanceLoginRequest

    try:
        # 解析请求
        login_request = FinanceLoginRequest(**request_data)

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
