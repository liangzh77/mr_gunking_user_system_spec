"""运营商个人信息管理API接口 (T069, T070)

此模块定义运营商个人信息相关的API端点。

端点:
- GET /v1/operators/me - 获取当前运营商个人信息 (T069)
- PUT /v1/operators/me - 更新当前运营商个人信息 (T070)

认证方式:
- JWT Token认证 (Authorization: Bearer {token})
- 用户类型要求: operator
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_db, require_operator
from ...schemas.operator import (
    BalanceResponse,
    OperatorProfile,
    OperatorUpdateRequest,
    RefundItem,
    RefundListResponse,
    SiteCreateRequest,
    SiteResponse,
    TransactionItem,
    TransactionListResponse,
    UsageItem,
    UsageListResponse,
)
from ...services.operator import OperatorService

router = APIRouter(prefix="/operators", tags=["运营商"])


@router.get(
    "/me",
    response_model=OperatorProfile,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "未认证或Token无效/过期"
        },
        403: {
            "description": "权限不足(非运营商用户)"
        },
        404: {
            "description": "运营商不存在"
        }
    },
    summary="获取个人信息",
    description="""
    获取当前登录运营商的完整个人信息。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **响应数据**:
    - operator_id: 运营商ID (UUID)
    - username: 用户名
    - name: 真实姓名或公司名
    - phone: 联系电话
    - email: 邮箱地址
    - category: 客户分类 (trial/normal/vip)
    - balance: 账户余额(字符串格式,精确到分)
    - is_active: 账户状态 (true=正常, false=已注销)
    - is_locked: 锁定状态 (true=已锁定, false=正常)
    - last_login_at: 最近登录时间 (可能为null)
    - created_at: 创建时间

    **注意事项**:
    - 不返回敏感信息如密码hash、API Key
    - balance为字符串避免浮点精度问题
    """
)
async def get_profile(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> OperatorProfile:
    """获取运营商个人信息API (T069)

    Args:
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        OperatorProfile: 运营商详细信息

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
    """
    operator_service = OperatorService(db)

    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token中缺少用户ID"
            }
        )

    try:
        operator_id = UUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_OPERATOR_ID",
                "message": f"无效的运营商ID格式: {operator_id_str}"
            }
        )

    # 调用服务层获取个人信息
    try:
        profile = await operator_service.get_profile(operator_id)
        return profile

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取个人信息失败: {str(e)}"
            }
        )


@router.put(
    "/me",
    response_model=OperatorProfile,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "请求参数错误(字段格式不正确)"
        },
        401: {
            "description": "未认证或Token无效/过期"
        },
        403: {
            "description": "权限不足(非运营商用户)"
        },
        404: {
            "description": "运营商不存在"
        }
    },
    summary="更新个人信息",
    description="""
    更新当前登录运营商的个人信息。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **允许更新的字段** (所有字段都是可选的):
    - name: 真实姓名或公司名 (2-50字符)
    - phone: 联系电话 (11位中国手机号)
    - email: 邮箱地址 (标准邮箱格式)

    **不允许更新的字段**:
    - username: 用户名 (创建后不可修改)
    - password: 密码 (请使用专用的修改密码接口)
    - balance: 余额 (通过充值/扣费接口修改)
    - category: 客户分类 (由管理员或系统自动调整)
    - is_active, is_locked: 账户状态 (由管理员或系统管理)

    **部分更新**:
    - 可以只提供需要更新的字段
    - 未提供的字段保持不变
    - 空body不会更新任何字段

    **响应数据**:
    - 返回更新后的完整个人信息 (OperatorProfile)
    """
)
async def update_profile(
    request: OperatorUpdateRequest,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> OperatorProfile:
    """更新运营商个人信息API (T070)

    Args:
        request: 更新请求数据 (name, phone, email都是可选)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        OperatorProfile: 更新后的完整个人信息

    Raises:
        HTTPException 400: 参数格式错误
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
    """
    operator_service = OperatorService(db)

    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token中缺少用户ID"
            }
        )

    try:
        operator_id = UUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_OPERATOR_ID",
                "message": f"无效的运营商ID格式: {operator_id_str}"
            }
        )

    # 调用服务层更新个人信息
    try:
        updated_profile = await operator_service.update_profile(operator_id, request)
        return updated_profile

    except HTTPException:
        # 重新抛出服务层异常
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"更新个人信息失败: {str(e)}"
            }
        )


@router.get(
    "/me/balance",
    response_model=BalanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "未认证或Token无效/过期"
        },
        403: {
            "description": "权限不足(非运营商用户)"
        },
        404: {
            "description": "运营商不存在"
        }
    },
    summary="查询账户余额",
    description="""
    查询当前登录运营商的账户余额和客户分类。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **响应数据**:
    - balance: 账户余额(字符串格式,精确到分)
    - category: 客户分类 (trial=试用, normal=普通, vip=VIP)

    **注意事项**:
    - balance为字符串避免浮点精度问题
    - 余额精确到分(小数点后两位)
    """
)
async def get_balance(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> BalanceResponse:
    """查询运营商账户余额API (T072)

    Args:
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        BalanceResponse: 余额和客户分类信息

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
    """
    operator_service = OperatorService(db)

    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token中缺少用户ID"
            }
        )

    try:
        operator_id = UUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_OPERATOR_ID",
                "message": f"无效的运营商ID格式: {operator_id_str}"
            }
        )

    # 调用服务层获取余额信息
    try:
        # 获取profile包含balance和category
        profile = await operator_service.get_profile(operator_id)

        return BalanceResponse(
            balance=profile.balance,
            category=profile.category
        )

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询余额失败: {str(e)}"
            }
        )


@router.get(
    "/me/transactions",
    response_model=TransactionListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "未认证或Token无效/过期"
        },
        403: {
            "description": "权限不足(非运营商用户)"
        },
        404: {
            "description": "运营商不存在"
        }
    },
    summary="查询交易记录",
    description="""
    查询当前登录运营商的交易记录(充值和消费流水)。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **查询参数**:
    - page: 页码(默认1,最小1)
    - page_size: 每页数量(默认20,最小1,最大100)
    - type: 交易类型过滤 (all=全部, recharge=充值, consumption=消费,默认all)
    - start_time: 开始时间(ISO 8601格式,可选)
    - end_time: 结束时间(ISO 8601格式,可选)

    **响应数据**:
    - page: 当前页码
    - page_size: 每页数量
    - total: 总记录数
    - items: 交易记录列表
      - transaction_id: 交易ID
      - type: 交易类型 (recharge/consumption)
      - amount: 交易金额(字符串格式)
      - balance_after: 交易后余额
      - created_at: 交易时间
      - related_usage_id: 关联使用记录ID(消费类型)
      - payment_method: 支付方式(充值类型): wechat/alipay

    **注意事项**:
    - 结果按交易时间降序排列(最新的在前)
    - amount和balance_after为字符串避免浮点精度问题
    """
)
async def get_transactions(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    type: str = Query("all", description="交易类型: all/recharge/consumption"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间")
) -> TransactionListResponse:
    """查询运营商交易记录API (T073)

    Args:
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话
        page: 页码
        page_size: 每页数量
        type: 交易类型过滤
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        TransactionListResponse: 分页的交易记录列表

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
    """
    operator_service = OperatorService(db)

    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token中缺少用户ID"
            }
        )

    try:
        operator_id = UUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_OPERATOR_ID",
                "message": f"无效的运营商ID格式: {operator_id_str}"
            }
        )

    # 验证type参数
    if type not in ["all", "recharge", "consumption"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_TYPE",
                "message": "type参数必须是: all, recharge 或 consumption"
            }
        )

    # 调用服务层获取交易记录
    try:
        transactions, total = await operator_service.get_transactions(
            operator_id=operator_id,
            page=page,
            page_size=page_size,
            transaction_type=type if type != "all" else None,
            start_time=start_time,
            end_time=end_time
        )

        # 转换为响应格式
        items = []
        for trans in transactions:
            items.append(TransactionItem(
                transaction_id=f"txn_{trans.id}",
                type=trans.transaction_type,
                amount=str(trans.amount),
                balance_after=str(trans.balance_after),
                created_at=trans.created_at,
                related_usage_id=f"usage_{trans.related_usage_id}" if trans.related_usage_id else None,
                payment_method=trans.payment_channel
            ))

        return TransactionListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items
        )

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询交易记录失败: {str(e)}"
            }
        )


@router.get(
    "/me/refunds",
    response_model=RefundListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "未认证或Token无效/过期"
        },
        403: {
            "description": "权限不足(非运营商用户)"
        },
        404: {
            "description": "运营商不存在"
        }
    },
    summary="查询退款记录",
    description="""
    查询当前登录运营商的退款申请记录。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **查询参数**:
    - page: 页码(默认1,最小1)
    - page_size: 每页数量(默认20,最小1,最大100)

    **响应数据**:
    - page: 当前页码
    - page_size: 每页数量
    - total: 总记录数
    - items: 退款记录列表
      - refund_id: 退款记录ID
      - requested_amount: 申请退款金额(字符串格式)
      - actual_refund_amount: 实际退款金额(字符串格式,可能为null)
      - status: 审核状态 (pending=待审核, approved=已通过, rejected=已拒绝)
      - reason: 退款原因
      - reject_reason: 拒绝原因(status=rejected时有值)
      - reviewed_by: 审核人ID(财务人员,可能为null)
      - reviewed_at: 审核时间(可能为null)
      - created_at: 申请时间

    **注意事项**:
    - 结果按申请时间降序排列(最新的在前)
    - 金额为字符串避免浮点精度问题
    """
)
async def get_refunds(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> RefundListResponse:
    """查询运营商退款记录API (T075)

    Args:
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话
        page: 页码
        page_size: 每页数量

    Returns:
        RefundListResponse: 分页的退款记录列表

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
    """
    operator_service = OperatorService(db)

    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token中缺少用户ID"
            }
        )

    try:
        operator_id = UUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_OPERATOR_ID",
                "message": f"无效的运营商ID格式: {operator_id_str}"
            }
        )

    # 调用服务层获取退款记录
    try:
        refunds, total = await operator_service.get_refunds(
            operator_id=operator_id,
            page=page,
            page_size=page_size
        )

        # 转换为响应格式
        items = []
        for refund in refunds:
            items.append(RefundItem(
                refund_id=f"refund_{refund.id}",
                requested_amount=str(refund.requested_amount),
                actual_refund_amount=str(refund.actual_refund_amount) if refund.actual_refund_amount else None,
                status=refund.status,
                reason=refund.reason,
                reject_reason=refund.reject_reason,
                reviewed_by=f"fin_{refund.reviewed_by}" if refund.reviewed_by else None,
                reviewed_at=refund.reviewed_at,
                created_at=refund.created_at
            ))

        return RefundListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items
        )

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询退款记录失败: {str(e)}"
            }
        )


@router.get(
    "/me/usage-records",
    response_model=UsageListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "未认证或Token无效/过期"
        },
        403: {
            "description": "权限不足(非运营商用户)"
        },
        404: {
            "description": "运营商不存在"
        },
        422: {
            "description": "查询参数验证失败"
        }
    },
    summary="查询使用记录",
    description="""
    查询当前登录运营商的游戏使用记录。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **查询参数**:
    - page: 页码(默认1,最小1)
    - page_size: 每页数量(默认20,最小1,最大100)
    - site_id: 运营点ID筛选(可选)
    - app_id: 应用ID筛选(可选)
    - start_time: 开始时间(ISO 8601格式,可选)
    - end_time: 结束时间(ISO 8601格式,可选)

    **响应数据**:
    - page: 当前页码
    - page_size: 每页数量
    - total: 总记录数
    - items: 使用记录列表
      - usage_id: 使用记录ID
      - session_id: 游戏会话ID(幂等性标识)
      - site_id: 运营点ID
      - site_name: 运营点名称
      - app_id: 应用ID
      - app_name: 应用名称
      - player_count: 玩家数量
      - unit_price: 单人价格(历史快照,字符串格式)
      - total_cost: 总费用(字符串格式)
      - game_duration: 游戏时长(秒,可能为null)
      - created_at: 授权时间(游戏启动时间)

    **注意事项**:
    - 结果按游戏启动时间降序排列(最新的在前)
    - 金额为字符串避免浮点精度问题
    - 支持多维度筛选(运营点、应用、时间范围)
    """
)
async def get_usage_records(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    site_id: Optional[str] = Query(None, description="运营点ID"),
    app_id: Optional[str] = Query(None, description="应用ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间")
) -> UsageListResponse:
    """查询运营商使用记录API (T102/T110)

    Args:
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话
        page: 页码
        page_size: 每页数量
        site_id: 运营点ID筛选
        app_id: 应用ID筛选
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        UsageListResponse: 分页的使用记录列表

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
        HTTPException 422: 参数验证失败
    """
    operator_service = OperatorService(db)

    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token中缺少用户ID"
            }
        )

    try:
        operator_id = UUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_OPERATOR_ID",
                "message": f"无效的运营商ID格式: {operator_id_str}"
            }
        )

    # 调用服务层获取使用记录
    try:
        usage_records, total = await operator_service.get_usage_records(
            operator_id=operator_id,
            page=page,
            page_size=page_size,
            site_id=site_id,
            app_id=app_id,
            start_time=start_time,
            end_time=end_time
        )

        # 转换为响应格式
        items = []
        for usage in usage_records:
            items.append(UsageItem(
                usage_id=f"usage_{usage.id}",
                session_id=usage.session_id,
                site_id=f"site_{usage.site_id}",
                site_name=usage.site.name,
                app_id=f"app_{usage.application_id}",
                app_name=usage.application.app_name,
                player_count=usage.player_count,
                unit_price=str(usage.price_per_player),
                total_cost=str(usage.total_cost),
                game_duration=usage.game_duration_minutes * 60 if usage.game_duration_minutes else None,  # 转换为秒
                created_at=usage.game_started_at
            ))

        return UsageListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items
        )

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询使用记录失败: {str(e)}"
            }
        )


# ========== 运营点管理接口 (T092-T096) ==========

@router.post(
    "/me/sites",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="创建运营点",
    description="创建新的运营点(门店/业务单元)"
)
async def create_site(
    request: SiteCreateRequest,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """创建运营点API (T092)

    Args:
        request: 创建运营点请求
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "message": "运营点创建成功",
            "data": SiteResponse对象
        }

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 404: 运营商不存在
        HTTPException 422: 参数验证失败
    """
    operator_service = OperatorService(db)

    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token中缺少用户ID"
            }
        )

    try:
        operator_id = UUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_OPERATOR_ID",
                "message": f"无效的运营商ID格式: {operator_id_str}"
            }
        )

    # 调用服务层创建运营点
    try:
        site = await operator_service.create_site(
            operator_id=operator_id,
            name=request.name,
            address=request.address,
            description=request.description
        )

        # 转换为响应格式
        site_response = SiteResponse(
            site_id=f"site_{site.id}",
            name=site.name,
            address=site.address,
            description=site.description,
            is_deleted=site.deleted_at is not None,
            created_at=site.created_at,
            updated_at=site.updated_at
        )

        return {
            "success": True,
            "message": "运营点创建成功",
            "data": site_response
        }

    except HTTPException:
        # 重新抛出服务层异常(404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"创建运营点失败: {str(e)}"
            }
        )
