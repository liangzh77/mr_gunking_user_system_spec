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
from ...schemas.invoice import InvoiceRequestCreate, InvoiceResponse
from ...schemas.operator import (
    ApplicationRequestCreate,
    ApplicationRequestItem,
    ApplicationRequestListResponse,
    AuthorizedApplicationItem,
    AuthorizedApplicationListResponse,
    BalanceResponse,
    OperatorProfile,
    OperatorUpdateRequest,
    RefundApplyRequest,
    RefundItem,
    RefundListResponse,
    SiteCreateRequest,
    SiteListResponse,
    SiteResponse,
    SiteUpdateRequest,
    TransactionItem,
    TransactionListResponse,
    UsageItem,
    UsageListResponse,
)
from ...schemas.payment import RechargeRequest, RechargeResponse
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


@router.post(
    "/me/recharge",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "description": "充值金额不符合要求(必须在10-10000元之间)"
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
    summary="发起充值",
    description="""
    创建充值订单并返回支付二维码。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **请求参数**:
    - amount: 充值金额(字符串格式,10-10000元,最多2位小数)
    - payment_method: 支付方式 (wechat=微信支付, alipay=支付宝)

    **业务规则**:
    - 充值金额范围: 10-10000元
    - 订单有效期: 30分钟
    - 支付成功后通过webhook回调更新余额

    **响应数据**:
    - order_id: 充值订单ID (格式: ord_recharge_<timestamp>_<uuid>)
    - amount: 充值金额(字符串格式)
    - payment_method: 支付方式 (wechat/alipay)
    - qr_code_url: 支付二维码URL(用于扫码支付)
    - payment_url: 支付页面URL(可选,用于H5场景)
    - expires_at: 订单过期时间(30分钟后)

    **注意事项**:
    - 订单30分钟内未支付将自动过期
    - 支付成功后余额实时更新
    - 支持微信和支付宝两种支付方式
    """
)
async def recharge(
    request: RechargeRequest,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """发起充值API (T071)

    Args:
        request: 充值请求(amount, payment_method)
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "message": "充值订单创建成功",
            "data": RechargeResponse对象
        }

    Raises:
        HTTPException 400: 充值金额不符合要求
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

    # 调用服务层创建充值订单
    try:
        recharge_order = await operator_service.create_recharge_order(
            operator_id=operator_id,
            amount=request.amount,
            payment_method=request.payment_method
        )

        # 转换为响应格式
        return {
            "success": True,
            "message": "充值订单创建成功",
            "data": RechargeResponse(
                order_id=recharge_order.order_id,
                amount=str(recharge_order.amount),
                payment_method=recharge_order.payment_method,
                qr_code_url=recharge_order.qr_code_url,
                payment_url=recharge_order.payment_url,
                expires_at=recharge_order.expires_at
            )
        }

    except HTTPException:
        # 重新抛出服务层异常(如404运营商不存在, 400金额错误)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"创建充值订单失败: {str(e)}"
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


@router.post(
    "/me/refunds",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "description": "余额为0无法申请退款"
        },
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
            "description": "参数验证失败(reason长度不符合要求)"
        }
    },
    summary="申请退款",
    description="""
    申请退款,仅退还当前账户余额(已消费金额不退)。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **请求参数**:
    - reason: 退款原因(10-500字符,必填)

    **业务规则**:
    - 只退当前余额,已消费金额不退
    - 余额为0时无法申请退款
    - 退款状态初始为pending(待审核)
    - requested_amount为申请时的余额快照

    **响应数据**:
    - refund_id: 退款申请ID (格式: refund_<uuid>)
    - requested_amount: 申请退款金额(字符串格式)
    - status: 审核状态 (pending)
    - reason: 退款原因
    - created_at: 申请时间

    **注意事项**:
    - 退款审核由财务人员处理
    - 支持多次申请退款
    - 金额为字符串避免浮点精度问题
    """
)
async def apply_refund(
    request: RefundApplyRequest,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """申请退款API (T074)

    Args:
        request: 退款申请请求(包含reason)
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "message": "退款申请已提交,待财务审核",
            "data": {
                "refund_id": "refund_<uuid>",
                "requested_amount": "500.00",
                "status": "pending",
                "reason": "...",
                "created_at": "2025-01-15T10:00:00Z",
                "actual_refund_amount": null,
                "reject_reason": null,
                "reviewed_by": null,
                "reviewed_at": null
            }
        }

    Raises:
        HTTPException 400: 余额为0无法申请退款
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

    # 调用服务层申请退款
    try:
        refund = await operator_service.apply_refund(
            operator_id=operator_id,
            reason=request.reason
        )

        # 转换为响应格式
        return {
            "success": True,
            "message": "退款申请已提交,待财务审核",
            "data": {
                "refund_id": f"refund_{refund.id}",
                "requested_amount": str(refund.requested_amount),
                "status": refund.status,
                "reason": refund.reason,
                "created_at": refund.created_at,
                "actual_refund_amount": None,
                "reject_reason": None,
                "reviewed_by": None,
                "reviewed_at": None
            }
        }

    except HTTPException:
        # 重新抛出服务层异常(如400余额为0, 404运营商不存在)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"申请退款失败: {str(e)}"
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


# ========== 发票管理接口 (T076-T077) ==========

@router.post(
    "/me/invoices",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "description": "开票金额超过已充值金额"
        },
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
            "description": "参数验证失败(金额/税号/抬头格式不正确)"
        }
    },
    summary="申请开具发票",
    description="""
    申请电子发票,财务审核通过后生成PDF下载链接。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **请求参数**:
    - amount: 开票金额(字符串格式,精确到分,不能超过已充值金额)
    - invoice_title: 发票抬头(公司名称,2-200字符)
    - tax_id: 纳税人识别号(15-20位大写字母数字)
    - email: 接收邮箱(可选,默认使用账户邮箱)

    **业务规则**:
    - 开票金额不能超过已充值金额
    - 税号格式必须符合要求(15-20位字母数字)
    - 发票状态初始为pending(待财务审核)
    - 审核通过后生成PDF链接

    **响应数据**:
    - invoice_id: 发票ID (格式: inv_<uuid>)
    - amount: 开票金额(字符串格式)
    - invoice_title: 发票抬头
    - tax_id: 纳税人识别号
    - email: 接收邮箱
    - status: 审核状态 (pending)
    - pdf_url: PDF下载链接(审核通过后才有)
    - created_at: 申请时间

    **注意事项**:
    - 财务审核后会生成电子发票PDF
    - 支持多次申请发票
    - 金额为字符串避免浮点精度问题
    """
)
async def apply_invoice(
    request: InvoiceRequestCreate,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """申请开具发票API (T076)

    Args:
        request: 发票申请请求
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "message": "发票申请已提交，等待财务审核",
            "data": InvoiceResponse对象
        }

    Raises:
        HTTPException 400: 开票金额超过已充值金额
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

    # 调用服务层申请发票
    try:
        invoice = await operator_service.apply_invoice(
            operator_id=operator_id,
            amount=request.amount,
            invoice_title=request.invoice_title,
            tax_id=request.tax_id,
            email=request.email
        )

        # 转换为响应格式
        return {
            "success": True,
            "message": "发票申请已提交，等待财务审核",
            "data": InvoiceResponse(
                invoice_id=f"inv_{invoice.id}",
                amount=str(invoice.amount),
                invoice_title=invoice.invoice_title,
                tax_id=invoice.tax_id,
                email=invoice.email,
                status=invoice.status,
                pdf_url=invoice.pdf_url,
                reviewed_by=f"fin_{invoice.reviewed_by}" if invoice.reviewed_by else None,
                reviewed_at=invoice.reviewed_at,
                created_at=invoice.created_at
            )
        }

    except HTTPException:
        # 重新抛出服务层异常(如400金额超限, 404运营商不存在)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"申请发票失败: {str(e)}"
            }
        )


@router.get(
    "/me/invoices",
    response_model=dict,
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
    summary="查询发票列表",
    description="""
    查询当前登录运营商的发票申请记录。

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
    - items: 发票记录列表
      - invoice_id: 发票ID
      - amount: 开票金额(字符串格式)
      - invoice_title: 发票抬头
      - tax_id: 纳税人识别号
      - email: 接收邮箱
      - status: 审核状态 (pending=待审核, approved=已通过, rejected=已拒绝)
      - pdf_url: PDF下载链接(status=approved时有值)
      - reviewed_by: 审核人ID(财务人员,可能为null)
      - reviewed_at: 审核时间(可能为null)
      - created_at: 申请时间

    **注意事项**:
    - 结果按申请时间降序排列(最新的在前)
    - 金额为字符串避免浮点精度问题
    - 已审核通过的发票可下载PDF
    """
)
async def get_invoices(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> dict:
    """查询运营商发票记录API (T077)

    Args:
        token: JWT Token payload
        db: 数据库会话
        page: 页码
        page_size: 每页数量

    Returns:
        dict: {
            "success": true,
            "data": {
                "page": 1,
                "page_size": 20,
                "total": 5,
                "items": [InvoiceResponse对象列表]
            }
        }

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

    # 调用服务层获取发票记录
    try:
        invoices, total = await operator_service.get_invoices(
            operator_id=operator_id,
            page=page,
            page_size=page_size
        )

        # 转换为响应格式
        items = []
        for invoice in invoices:
            items.append(InvoiceResponse(
                invoice_id=f"inv_{invoice.id}",
                amount=str(invoice.amount),
                invoice_title=invoice.invoice_title,
                tax_id=invoice.tax_id,
                email=invoice.email,
                status=invoice.status,
                pdf_url=invoice.pdf_url,
                reviewed_by=f"fin_{invoice.reviewed_by}" if invoice.reviewed_by else None,
                reviewed_at=invoice.reviewed_at,
                created_at=invoice.created_at
            ))

        return {
            "success": True,
            "data": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "items": items
            }
        }

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询发票记录失败: {str(e)}"
            }
        )


@router.get(
    "/me/usage-records",
    response_model=dict,
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

        return {
            "success": True,
            "data": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "items": items
            }
        }

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


@router.get(
    "/me/usage-records/{record_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="查询使用记录详情",
    description="根据记录ID查询单条使用记录的详细信息"
)
async def get_usage_record(
    record_id: str,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """查询使用记录详情API (T111)

    Args:
        record_id: 使用记录ID (格式: usage_<uuid>)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "data": UsageItem对象
        }

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 404: 使用记录不存在或无权访问
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

    # 解析record_id
    try:
        if record_id.startswith("usage_"):
            usage_uuid = UUID(record_id[6:])
        else:
            usage_uuid = UUID(record_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_RECORD_ID",
                "message": f"无效的使用记录ID格式: {record_id}"
            }
        )

    # 调用服务层获取使用记录详情
    try:
        usage_record = await operator_service.get_usage_record(
            operator_id=operator_id,
            record_id=usage_uuid
        )

        # 转换为响应格式
        usage_item = UsageItem(
            usage_id=f"usage_{usage_record.id}",
            session_id=usage_record.session_id,
            site_id=f"site_{usage_record.site_id}",
            site_name=usage_record.site.name,
            app_id=f"app_{usage_record.application_id}",
            app_name=usage_record.application.app_name,
            player_count=usage_record.player_count,
            unit_price=str(usage_record.price_per_player),
            total_cost=str(usage_record.total_cost),
            game_duration=usage_record.game_duration_minutes * 60 if usage_record.game_duration_minutes else None,
            created_at=usage_record.game_started_at
        )

        return {
            "success": True,
            "data": usage_item
        }

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询使用记录详情失败: {str(e)}"
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


@router.get(
    "/me/sites",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="查询运营点列表",
    description="获取当前运营商的所有运营点列表"
)
async def get_sites(
    include_deleted: bool = Query(False, description="是否包含已删除的运营点"),
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """查询运营点列表API (T093)

    Args:
        include_deleted: 是否包含已删除的运营点
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "data": {
                "sites": [SiteResponse对象列表]
            }
        }

    Raises:
        HTTPException 401: 未认证或Token无效
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

    # 调用服务层获取运营点列表
    try:
        sites = await operator_service.get_sites(
            operator_id=operator_id,
            include_deleted=include_deleted
        )

        # 转换为响应格式
        site_responses = []
        for site in sites:
            site_responses.append(SiteResponse(
                site_id=f"site_{site.id}",
                name=site.name,
                address=site.address,
                description=site.description,
                is_deleted=site.deleted_at is not None,
                created_at=site.created_at,
                updated_at=site.updated_at
            ))

        return {
            "success": True,
            "data": {
                "sites": site_responses
            }
        }

    except HTTPException:
        # 重新抛出服务层异常(404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询运营点列表失败: {str(e)}"
            }
        )


@router.put(
    "/me/sites/{site_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="更新运营点信息",
    description="更新运营点的名称、地址、描述"
)
async def update_site(
    site_id: str,
    request: SiteUpdateRequest,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """更新运营点API (T095)

    Args:
        site_id: 运营点ID (格式: site_<uuid>)
        request: 更新运营点请求
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "message": "运营点信息已更新",
            "data": SiteResponse对象
        }

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 404: 运营商或运营点不存在
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

    # 解析site_id
    try:
        if site_id.startswith("site_"):
            site_uuid = UUID(site_id[5:])
        else:
            site_uuid = UUID(site_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_SITE_ID",
                "message": f"无效的运营点ID格式: {site_id}"
            }
        )

    # 调用服务层更新运营点
    try:
        site = await operator_service.update_site(
            operator_id=operator_id,
            site_id=site_uuid,
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
            "message": "运营点信息已更新",
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
                "message": f"更新运营点失败: {str(e)}"
            }
        )


@router.delete(
    "/me/sites/{site_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="删除运营点",
    description="删除运营点(逻辑删除),历史数据保留"
)
async def delete_site(
    site_id: str,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """删除运营点API (T096)

    Args:
        site_id: 运营点ID (格式: site_<uuid>)
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "message": "运营点已删除"
        }

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 404: 运营商或运营点不存在
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

    # 解析site_id
    try:
        if site_id.startswith("site_"):
            site_uuid = UUID(site_id[5:])
        else:
            site_uuid = UUID(site_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_SITE_ID",
                "message": f"无效的运营点ID格式: {site_id}"
            }
        )

    # 调用服务层删除运营点
    try:
        await operator_service.delete_site(
            operator_id=operator_id,
            site_id=site_uuid
        )

        return {
            "success": True,
            "message": "运营点已删除"
        }

    except HTTPException:
        # 重新抛出服务层异常(404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"删除运营点失败: {str(e)}"
            }
        )


# ========== 使用统计接口 (T112-T114) ==========

@router.get(
    "/me/statistics/by-site",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="按运营点统计",
    description="查询各运营点的使用情况统计(场次、玩家、消费)"
)
async def get_statistics_by_site(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """按运营点统计API (T112)

    Args:
        start_time: 开始时间(可选)
        end_time: 结束时间(可选)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "data": {
                "sites": [
                    {
                        "site_id": "site_xxx",
                        "site_name": "北京朝阳门店",
                        "total_sessions": 60,
                        "total_players": 270,
                        "total_cost": "2700.00"
                    }
                ]
            }
        }

    Raises:
        HTTPException 401: 未认证或Token无效
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

    # 调用服务层获取统计数据
    try:
        statistics = await operator_service.get_statistics_by_site(
            operator_id=operator_id,
            start_time=start_time,
            end_time=end_time
        )

        return {
            "success": True,
            "data": {
                "sites": statistics
            }
        }

    except HTTPException:
        # 重新抛出服务层异常(404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询统计数据失败: {str(e)}"
            }
        )


@router.get(
    "/me/statistics/by-app",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="按应用统计",
    description="查询各应用的使用情况统计(场次、玩家、平均每场玩家数、消费)"
)
async def get_statistics_by_app(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """按应用统计API (T113)

    Args:
        start_time: 开始时间(可选)
        end_time: 结束时间(可选)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "data": {
                "applications": [
                    {
                        "app_id": "app_xxx",
                        "app_name": "太空探险",
                        "total_sessions": 80,
                        "total_players": 360,
                        "avg_players_per_session": 4.5,
                        "total_cost": "3600.00"
                    }
                ]
            }
        }

    Raises:
        HTTPException 401: 未认证或Token无效
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

    # 调用服务层获取统计数据
    try:
        statistics = await operator_service.get_statistics_by_app(
            operator_id=operator_id,
            start_time=start_time,
            end_time=end_time
        )

        return {
            "success": True,
            "data": {
                "applications": statistics
            }
        }

    except HTTPException:
        # 重新抛出服务层异常(404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询统计数据失败: {str(e)}"
            }
        )


@router.get(
    "/me/statistics/consumption",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="消费统计(按时间)",
    description="查询消费趋势,支持按天/周/月维度聚合,返回图表数据和汇总统计"
)
async def get_consumption_statistics(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    dimension: str = Query("day", description="时间维度: day/week/month"),
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """按时间统计消费API (T114)

    Args:
        start_time: 开始时间(可选)
        end_time: 结束时间(可选)
        dimension: 时间维度 (day/week/month)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "data": {
                "dimension": "day",
                "chart_data": [
                    {
                        "date": "2025-01-15",
                        "total_sessions": 10,
                        "total_players": 45,
                        "total_cost": "450.00"
                    }
                ],
                "summary": {
                    "total_sessions": 100,
                    "total_players": 450,
                    "total_cost": "4500.00",
                    "avg_players_per_session": 4.5
                }
            }
        }

    Raises:
        HTTPException 400: dimension参数无效
        HTTPException 401: 未认证或Token无效
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

    # 验证dimension参数
    if dimension not in ["day", "week", "month"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_DIMENSION",
                "message": "dimension参数必须是: day, week 或 month"
            }
        )

    # 调用服务层获取消费统计
    try:
        statistics = await operator_service.get_consumption_statistics(
            operator_id=operator_id,
            start_time=start_time,
            end_time=end_time,
            dimension=dimension
        )

        return {
            "success": True,
            "data": statistics
        }

    except HTTPException:
        # 重新抛出服务层异常(404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询消费统计失败: {str(e)}"
            }
        )


@router.get(
    "/me/statistics/player-distribution",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="玩家数量分布统计",
    description="统计不同玩家数量的游戏场次分布,用于分析最常见的游戏规模"
)
async def get_player_distribution(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """玩家数量分布统计API (T115)

    Args:
        start_time: 开始时间(可选)
        end_time: 结束时间(可选)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "data": {
                "distribution": [
                    {
                        "player_count": 4,
                        "session_count": 25,
                        "percentage": 25.0,
                        "total_cost": "1000.00"
                    }
                ],
                "total_sessions": 100,
                "most_common_player_count": 4
            }
        }

    Raises:
        HTTPException 401: 未认证或Token无效
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

    # 调用服务层获取玩家数量分布统计
    try:
        statistics = await operator_service.get_player_distribution_statistics(
            operator_id=operator_id,
            start_time=start_time,
            end_time=end_time
        )

        return {
            "success": True,
            "data": statistics
        }

    except HTTPException:
        # 重新抛出服务层异常(404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询玩家分布统计失败: {str(e)}"
            }
        )


# ========== 数据导出接口 (T116-T117) ==========

@router.get(
    "/me/usage-records/export",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="导出使用记录",
    description="导出使用记录到Excel或CSV文件(模拟实现)"
)
async def export_usage_records(
    format: str = Query("excel", description="导出格式: excel或csv"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    site_id: Optional[str] = Query(None, description="运营点ID筛选"),
    app_id: Optional[str] = Query(None, description="应用ID筛选"),
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """导出使用记录API (T116 - 模拟实现)

    Args:
        format: 导出格式 (excel/csv)
        start_time: 开始时间(可选)
        end_time: 结束时间(可选)
        site_id: 运营点ID筛选(可选)
        app_id: 应用ID筛选(可选)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "data": {
                "export_id": "export_xxx",
                "filename": "usage_records_20250115.xlsx",
                "format": "excel",
                "download_url": "https://storage.example.com/exports/xxx.xlsx",
                "file_size": 102400,
                "expires_at": "2025-01-15T12:30:00Z",
                "created_at": "2025-01-15T12:00:00Z"
            }
        }

    Raises:
        HTTPException 400: 格式参数无效
        HTTPException 401: 未认证或Token无效
        HTTPException 404: 运营商不存在
    """
    from datetime import timedelta
    import uuid

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

    # 验证format参数
    if format not in ["excel", "csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": "format参数必须是: excel 或 csv"
            }
        )

    # 验证运营商存在
    try:
        await operator_service.get_profile(operator_id)
    except HTTPException:
        raise

    # 模拟导出实现
    export_id = f"export_{uuid.uuid4()}"
    file_ext = "xlsx" if format == "excel" else "csv"
    filename = f"usage_records_{datetime.now().strftime('%Y%m%d')}.{file_ext}"
    created_at = datetime.now()
    expires_at = created_at + timedelta(minutes=30)

    return {
        "success": True,
        "data": {
            "export_id": export_id,
            "filename": filename,
            "format": format,
            "download_url": f"https://storage.example.com/exports/{filename}",
            "file_size": 102400,  # 模拟文件大小100KB
            "expires_at": expires_at,
            "created_at": created_at
        }
    }


@router.get(
    "/me/statistics/export",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="导出统计报表",
    description="导出统计报表到Excel或CSV文件(模拟实现)"
)
async def export_statistics(
    format: str = Query("excel", description="导出格式: excel或csv"),
    report_type: str = Query(..., description="报表类型: site/application/consumption/player_distribution"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    dimension: Optional[str] = Query(None, description="时间维度(consumption报表): day/week/month"),
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """导出统计报表API (T117 - 模拟实现)

    Args:
        format: 导出格式 (excel/csv)
        report_type: 报表类型 (site/application/consumption/player_distribution)
        start_time: 开始时间(可选)
        end_time: 结束时间(可选)
        dimension: 时间维度(可选,仅consumption报表)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "data": {
                "export_id": "export_xxx",
                "filename": "statistics_by_site_20250115.xlsx",
                "format": "excel",
                "download_url": "https://storage.example.com/exports/xxx.xlsx",
                "file_size": 51200,
                "expires_at": "2025-01-15T12:30:00Z",
                "created_at": "2025-01-15T12:00:00Z"
            }
        }

    Raises:
        HTTPException 400: 参数无效
        HTTPException 401: 未认证或Token无效
        HTTPException 404: 运营商不存在
    """
    from datetime import timedelta
    import uuid

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

    # 验证format参数
    if format not in ["excel", "csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": "format参数必须是: excel 或 csv"
            }
        )

    # 验证report_type参数
    valid_report_types = ["site", "application", "consumption", "player_distribution"]
    if report_type not in valid_report_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_REPORT_TYPE",
                "message": f"report_type参数必须是: {', '.join(valid_report_types)}"
            }
        )

    # 验证dimension参数(如果是consumption报表)
    if report_type == "consumption" and dimension and dimension not in ["day", "week", "month"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_DIMENSION",
                "message": "dimension参数必须是: day, week 或 month"
            }
        )

    # 验证运营商存在
    try:
        await operator_service.get_profile(operator_id)
    except HTTPException:
        raise

    # 模拟导出实现
    export_id = f"export_{uuid.uuid4()}"
    file_ext = "xlsx" if format == "excel" else "csv"
    report_name_map = {
        "site": "by_site",
        "application": "by_application",
        "consumption": "consumption",
        "player_distribution": "player_distribution"
    }
    filename = f"statistics_{report_name_map[report_type]}_{datetime.now().strftime('%Y%m%d')}.{file_ext}"
    created_at = datetime.now()
    expires_at = created_at + timedelta(minutes=30)

    return {
        "success": True,
        "data": {
            "export_id": export_id,
            "filename": filename,
            "format": format,
            "download_url": f"https://storage.example.com/exports/{filename}",
            "file_size": 51200,  # 模拟文件大小50KB
            "expires_at": expires_at,
            "created_at": created_at
        }
    }


# ========== 应用授权管理接口 (T097-T099) ==========

@router.get(
    "/me/applications",
    response_model=dict,
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
    summary="查询已授权应用",
    description="""
    查询当前登录运营商已授权的应用列表。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **响应数据**:
    - applications: 已授权应用列表
      - app_id: 应用ID
      - app_code: 应用唯一标识符
      - app_name: 应用名称
      - description: 应用描述
      - price_per_player: 单人价格
      - min_players: 最小玩家数
      - max_players: 最大玩家数
      - authorized_at: 授权时间
      - expires_at: 授权到期时间(null表示永久授权)

    **注意事项**:
    - 只返回活跃且未过期的授权
    - 按授权时间降序排列(最新的在前)
    """
)
async def get_authorized_applications(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """查询运营商已授权应用列表API (T097)

    Args:
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "data": AuthorizedApplicationListResponse对象
        }

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

    # 调用服务层获取已授权应用列表
    try:
        applications = await operator_service.get_authorized_applications(
            operator_id=operator_id
        )

        # 转换为响应格式
        app_items = []
        for app in applications:
            app_items.append(AuthorizedApplicationItem(
                app_id=app["app_id"],
                app_code=app["app_code"],
                app_name=app["app_name"],
                description=app["description"],
                price_per_player=app["price_per_player"],
                min_players=app["min_players"],
                max_players=app["max_players"],
                authorized_at=app["authorized_at"],
                expires_at=app["expires_at"],
                is_active=True  # 服务层已筛选,均为活跃授权
            ))

        return {
            "success": True,
            "data": AuthorizedApplicationListResponse(
                applications=app_items
            )
        }

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询已授权应用失败: {str(e)}"
            }
        )


@router.post(
    "/me/applications/requests",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "description": "不能重复申请或已授权"
        },
        401: {
            "description": "未认证或Token无效/过期"
        },
        403: {
            "description": "权限不足(非运营商用户)"
        },
        404: {
            "description": "运营商或应用不存在"
        },
        422: {
            "description": "参数验证失败(app_id格式不正确或reason长度不符合要求)"
        }
    },
    summary="申请应用授权",
    description="""
    申请使用某个应用的授权,需要管理员审批。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **请求参数**:
    - app_id: 应用ID(格式: app_<uuid>)
    - reason: 申请理由(10-500字符,必填)

    **业务规则**:
    - 不能重复申请(同一应用只能有一条pending申请)
    - 不能申请已授权的应用
    - 应用必须存在且is_active=true

    **响应数据**:
    - request_id: 申请ID (格式: req_<uuid>)
    - app_id: 应用ID
    - app_name: 应用名称
    - reason: 申请理由
    - status: 审核状态 (pending)
    - created_at: 申请时间

    **注意事项**:
    - 申请提交后需等待管理员审核
    - 审核通过后自动创建授权关系
    """
)
async def create_application_request(
    request: ApplicationRequestCreate,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """申请应用授权API (T098)

    Args:
        request: 授权申请请求(app_id, reason)
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        dict: {
            "success": true,
            "message": "授权申请已提交,待管理员审核",
            "data": {
                "request_id": "req_<uuid>",
                "app_id": "app_<uuid>",
                "app_name": "...",
                "reason": "...",
                "status": "pending",
                "created_at": "2025-01-15T10:00:00Z"
            }
        }

    Raises:
        HTTPException 400: 不能重复申请或已授权
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 404: 运营商或应用不存在
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

    # 解析app_id
    try:
        if request.app_id.startswith("app_"):
            app_uuid = UUID(request.app_id[4:])
        else:
            app_uuid = UUID(request.app_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_APP_ID",
                "message": f"无效的应用ID格式: {request.app_id}"
            }
        )

    # 调用服务层创建授权申请
    try:
        app_request = await operator_service.create_application_request(
            operator_id=operator_id,
            application_id=app_uuid,
            reason=request.reason
        )

        # 转换为响应格式
        return {
            "success": True,
            "message": "授权申请已提交,待管理员审核",
            "data": {
                "request_id": f"req_{app_request.id}",
                "app_id": f"app_{app_request.application_id}",
                "app_name": app_request.application.app_name,
                "reason": app_request.reason,
                "status": app_request.status,
                "created_at": app_request.created_at
            }
        }

    except HTTPException:
        # 重新抛出服务层异常(如400重复申请, 404运营商/应用不存在)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"提交授权申请失败: {str(e)}"
            }
        )


@router.get(
    "/me/applications/requests",
    response_model=dict,
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
    summary="查询授权申请列表",
    description="""
    查询当前登录运营商的应用授权申请记录(分页)。

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
    - items: 申请记录列表
      - request_id: 申请ID
      - app_id: 应用ID
      - app_name: 应用名称
      - reason: 申请理由
      - status: 审核状态 (pending=待审核, approved=已通过, rejected=已拒绝)
      - reject_reason: 拒绝原因(status=rejected时有值)
      - reviewed_by: 审核人ID(管理员,可能为null)
      - reviewed_at: 审核时间(可能为null)
      - created_at: 申请时间

    **注意事项**:
    - 结果按申请时间降序排列(最新的在前)
    - 包含所有状态的申请记录(pending/approved/rejected)
    """
)
async def get_application_requests(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> dict:
    """查询运营商授权申请列表API (T099)

    Args:
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话
        page: 页码
        page_size: 每页数量

    Returns:
        dict: {
            "success": true,
            "data": ApplicationRequestListResponse对象
        }

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

    # 调用服务层获取授权申请列表
    try:
        requests_list, total = await operator_service.get_application_requests(
            operator_id=operator_id,
            page=page,
            page_size=page_size
        )

        # 转换为响应格式
        items = []
        for req in requests_list:
            items.append(ApplicationRequestItem(
                request_id=f"req_{req.id}",
                app_id=f"app_{req.application_id}",
                app_code=req.application.app_code,
                app_name=req.application.app_name,
                reason=req.reason,
                status=req.status,
                reject_reason=req.reject_reason,
                reviewed_by=f"admin_{req.reviewed_by}" if req.reviewed_by else None,
                reviewed_at=req.reviewed_at,
                created_at=req.created_at
            ))

        return {
            "success": True,
            "data": ApplicationRequestListResponse(
                page=page,
                page_size=page_size,
                total=total,
                items=items
            )
        }

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询授权申请列表失败: {str(e)}"
            }
        )
