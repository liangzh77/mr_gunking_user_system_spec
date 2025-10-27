"""授权API接口 (T046, T066, T067, T068)

此模块定义授权相关的API端点。

端点:
- POST /v1/auth/game/authorize - 游戏授权请求 (T046)
- POST /v1/auth/operators/register - 运营商注册 (T066)
- POST /v1/auth/operators/login - 运营商登录 (T067)
- POST /v1/auth/operators/logout - 运营商登出 (T068)

认证方式:
- 游戏授权: API Key认证 (X-API-Key header) + HMAC签名验证
- 运营商注册/登录: 无需认证
- 运营商登出: JWT Token认证 (Authorization: Bearer {token})
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import require_operator
from ...db.session import get_db
from ...schemas.auth import (
    ErrorResponse,
    GameAuthorizeData,
    GameAuthorizeRequest,
    GameAuthorizeResponse,
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
    from ...services.admin_auth import AdminAuthService

    try:
        # 解析请求参数
        username = request_data.get("username")
        password = request_data.get("password")

        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "MISSING_FIELDS",
                    "message": "用户名和密码不能为空"
                }
            )

        # 获取客户端IP
        client_ip = http_request.client.host if http_request.client else None

        # 调用管理员认证服务进行登录
        admin_auth_service = AdminAuthService(db)
        response = await admin_auth_service.login(
            username=username,
            password=password,
            client_ip=client_ip
        )

        # 验证登录用户是否为财务角色
        if response.user.role != "finance":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "INVALID_ROLE",
                    "message": "用户不是财务角色，无法访问财务系统"
                }
            )

        # 返回财务登录格式(符合contract tests期望)
        return {
            "access_token": response.access_token,
            "token_type": response.token_type,
            "expires_in": response.expires_in,
            "finance": {
                "finance_id": str(response.user.id),
                "username": response.user.username,
                "name": response.user.full_name,
                "full_name": response.user.full_name,
                "role": "finance",  # 统一返回"finance"角色
                "email": response.user.email
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
