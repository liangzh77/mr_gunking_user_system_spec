"""财务后台业务API接口 (T175-T186)

此模块定义财务人员业务操作相关的API端点。

端点分类:
1. Dashboard数据看板 (T175-T178):
   - GET /v1/finance/dashboard - 今日收入概览
   - GET /v1/finance/dashboard/trends - 月度收入趋势
   - GET /v1/finance/top-customers - 消费金额Top客户
   - GET /v1/finance/customers/{operator_id}/details - 客户详细财务信息

2. 退款审核 (T181-T184):
   - GET /v1/finance/refunds - 退款申请列表
   - GET /v1/finance/refunds/{refund_id} - 退款申请详情
   - POST /v1/finance/refunds/{refund_id}/approve - 批准退款
   - POST /v1/finance/refunds/{refund_id}/reject - 拒绝退款

3. 开票审核 (T185-T186):
   - GET /v1/finance/invoices - 开票申请列表
   - POST /v1/finance/invoices/{invoice_id}/approve - 批准开票
   - POST /v1/finance/invoices/{invoice_id}/reject - 拒绝开票

认证方式:
- JWT Token认证 (Authorization: Bearer {token})
- 用户类型要求: finance
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Form, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_db, require_finance
from ...core import BadRequestException, NotFoundException
from ...schemas.finance import (
    AuditLogListResponse,
    CustomerFinanceDetails,
    DashboardOverview,
    DashboardTrends,
    InvoiceApproveRequest,
    InvoiceListResponse,
    InvoiceApproveResponse,
    RechargeRequest,
    RechargeResponse,
    RefundApproveRequest,
    RefundApproveResponse,
    RefundDetailsResponse,
    RefundListResponse,
    RefundRejectRequest,
    ReportGenerateRequest,
    ReportGenerateResponse,
    ReportListResponse,
    TopCustomersResponse,
)
from ...services.finance_dashboard_service import FinanceDashboardService
from ...services.finance_invoice_service import FinanceInvoiceService
from ...services.finance_refund_service import FinanceRefundService

router = APIRouter(prefix="/finance", tags=["财务后台"])


# ==================== Dashboard数据看板 (T175-T178) ====================


@router.get(
    "/dashboard",
    response_model=DashboardOverview,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
    },
    summary="今日收入概览",
    description="""
    获取今日(UTC 00:00-23:59)的财务数据概览。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **响应数据**:
    - today_recharge: 今日充值总额(字符串格式,精确到分)
    - today_consumption: 今日消费总额
    - today_refund: 今日退款总额
    - today_net_income: 今日净收入(充值-退款)
    - total_operators: 总运营商数量(活跃,未删除)
    - active_operators_today: 今日活跃运营商数(有交易记录)

    **业务规则**:
    - 使用UTC时区计算今日范围
    - 净收入 = 充值 - 退款(不扣除消费,因为消费已在余额中)
    - 活跃运营商 = 今日有任意类型交易记录的运营商
    """,
)
async def get_dashboard(
    token: dict = Depends(require_finance), db: AsyncSession = Depends(get_db)
) -> DashboardOverview:
    """获取今日收入概览API (T175)

    Args:
        token: JWT Token payload (包含sub=finance_id, user_type=finance)
        db: 数据库会话

    Returns:
        DashboardOverview: 今日财务概览数据

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 500: 服务器内部错误
    """
    try:
        dashboard_service = FinanceDashboardService(db)
        overview = await dashboard_service.get_dashboard_overview()
        return overview

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取Dashboard数据失败: {str(e)}",
            },
        )


@router.get(
    "/dashboard/trends",
    response_model=DashboardTrends,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "请求参数错误(月份格式不正确)"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
    },
    summary="月度收入趋势",
    description="""
    获取指定月份的每日收入趋势数据,用于绘制趋势图表。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **查询参数**:
    - month: 月份(YYYY-MM格式,可选,默认当前月)

    **响应数据**:
    - month: 查询的月份(YYYY-MM格式)
    - chart_data: 每日数据数组,包含该月所有天(即使无数据也显示0)
      - date: 日期(YYYY-MM-DD)
      - recharge: 当日充值
      - consumption: 当日消费
      - refund: 当日退款
      - net_income: 当日净收入(充值-退款)
    - summary: 月度汇总
      - total_recharge: 月度总充值
      - total_consumption: 月度总消费
      - total_refund: 月度总退款
      - total_net_income: 月度总净收入

    **业务规则**:
    - 返回完整月份数据(1-28/29/30/31日)
    - 无交易的日期显示为"0.00"
    - 使用UTC时区
    """,
)
async def get_dashboard_trends(
    month: Optional[str] = Query(None, description="月份(YYYY-MM格式,默认当前月)"),
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> DashboardTrends:
    """获取月度收入趋势API (T176)

    Args:
        month: 查询月份(YYYY-MM格式)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        DashboardTrends: 月度趋势数据

    Raises:
        HTTPException 400: 月份格式错误
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 500: 服务器内部错误
    """
    try:
        dashboard_service = FinanceDashboardService(db)
        trends = await dashboard_service.get_dashboard_trends(month)
        return trends

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_MONTH", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取趋势数据失败: {str(e)}",
            },
        )


@router.get(
    "/top-customers",
    response_model=TopCustomersResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "请求参数错误(limit超出范围)"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
    },
    summary="消费金额Top客户",
    description="""
    获取消费金额排名靠前的客户列表。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **查询参数**:
    - limit: 返回Top N客户(1-100,默认10)

    **响应数据**:
    - customers: Top客户列表(按消费金额降序)
      - rank: 排名(1-N)
      - operator_id: 运营商ID
      - operator_name: 运营商名称
      - category: 客户分类(trial/normal/vip)
      - total_consumption: 累计消费金额
      - consumption_percentage: 占总消费百分比(保留2位小数)
      - total_sessions: 累计游戏场次
    - total_consumption: 所有客户总消费金额

    **业务规则**:
    - 仅统计消费类型交易(consumption)
    - 按消费金额降序排列
    - 百分比 = (客户消费 / 总消费) * 100
    """,
)
async def get_top_customers(
    limit: int = Query(10, ge=1, le=100, description="返回Top N客户"),
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> TopCustomersResponse:
    """获取消费金额Top客户API (T177)

    Args:
        limit: 返回Top N客户
        token: JWT Token payload
        db: 数据库会话

    Returns:
        TopCustomersResponse: Top客户列表

    Raises:
        HTTPException 400: limit超出范围
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 500: 服务器内部错误
    """
    try:
        dashboard_service = FinanceDashboardService(db)
        top_customers = await dashboard_service.get_top_customers(limit=limit)
        return top_customers

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_LIMIT", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取Top客户失败: {str(e)}",
            },
        )


@router.get(
    "/customers/{operator_id}/details",
    response_model=CustomerFinanceDetails,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "运营商ID格式错误"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
        404: {"description": "运营商不存在"},
    },
    summary="客户详细财务信息",
    description="""
    获取指定客户的详细财务数据。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **路径参数**:
    - operator_id: 运营商ID(UUID格式)

    **响应数据**:
    - operator_id: 运营商ID
    - operator_name: 运营商名称
    - category: 客户分类
    - current_balance: 当前余额
    - total_recharged: 累计充值金额
    - total_consumed: 累计消费金额
    - total_refunded: 累计退款金额
    - total_sessions: 累计游戏场次
    - first_transaction_at: 首次交易时间
    - last_transaction_at: 最近交易时间

    **业务规则**:
    - 统计该运营商所有历史交易记录
    - 用于审核退款时评估客户价值
    """,
)
async def get_customer_finance_details(
    operator_id: str,
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> CustomerFinanceDetails:
    """获取客户详细财务信息API (T178)

    Args:
        operator_id: 运营商ID
        token: JWT Token payload
        db: 数据库会话

    Returns:
        CustomerFinanceDetails: 客户财务详情

    Raises:
        HTTPException 400: ID格式错误
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
        HTTPException 500: 服务器内部错误
    """
    try:
        dashboard_service = FinanceDashboardService(db)
        details = await dashboard_service.get_customer_finance_details(operator_id)
        return details

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_OPERATOR_ID", "message": str(e)},
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "OPERATOR_NOT_FOUND", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取客户财务详情失败: {str(e)}",
            },
        )


# ==================== 退款审核 (T181-T184) ====================


@router.get(
    "/refunds",
    response_model=RefundListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
    },
    summary="退款申请列表",
    description="""
    获取退款申请列表,支持分页和状态筛选。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **查询参数**:
    - status: 状态筛选(pending/approved/rejected/all,默认all)
    - page: 页码(从1开始,默认1)
    - page_size: 每页条数(1-100,默认20)

    **响应数据**:
    - page: 当前页码
    - page_size: 每页条数
    - total: 符合条件的总记录数
    - items: 退款申请列表(按创建时间倒序)
      - refund_id: 退款申请ID
      - operator_id: 运营商ID
      - operator_name: 运营商名称
      - operator_category: 客户分类
      - requested_amount: 申请退款金额
      - current_balance: 当前余额
      - actual_refund_amount: 实际退款金额(已审核时)
      - status: 状态(pending/approved/rejected)
      - reason: 退款原因
      - reject_reason: 拒绝原因(已拒绝时)
      - reviewed_by: 审核人ID
      - reviewed_at: 审核时间
      - created_at: 申请创建时间

    **业务规则**:
    - 按创建时间倒序(最新申请在前)
    - 实际退款金额可能小于申请金额(以当前余额为准)
    """,
)
async def get_refunds(
    status: Optional[str] = Query("all", description="状态筛选(pending/approved/rejected/all)"),
    page: int = Query(1, ge=1, description="页码(从1开始)"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> RefundListResponse:
    """获取退款申请列表API (T181)

    Args:
        status: 状态筛选
        page: 页码
        page_size: 每页条数
        token: JWT Token payload
        db: 数据库会话

    Returns:
        RefundListResponse: 分页的退款申请列表

    Raises:
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 500: 服务器内部错误
    """
    try:
        refund_service = FinanceRefundService(db)
        refunds = await refund_service.get_refunds(
            status=status, page=page, page_size=page_size
        )
        return refunds

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取退款列表失败: {str(e)}",
            },
        )


@router.get(
    "/refunds/{refund_id}",
    response_model=RefundDetailsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "退款ID格式错误"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
        404: {"description": "退款申请不存在"},
    },
    summary="退款申请详情",
    description="""
    获取退款申请的详细信息,包含运营商财务概况。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **路径参数**:
    - refund_id: 退款申请ID(UUID格式)

    **响应数据**:
    - 退款申请基本信息(同列表接口)
    - operator_finance: 运营商财务概况
      - operator_id: 运营商ID
      - operator_name: 运营商名称
      - category: 客户分类
      - current_balance: 当前余额
      - total_recharged: 累计充值
      - total_consumed: 累计消费
      - total_refunded: 累计退款
      - total_sessions: 累计场次
      - first_transaction_at: 首次交易时间
      - last_transaction_at: 最近交易时间

    **业务规则**:
    - 用于审核前评估客户价值和退款合理性
    - 财务数据统计包含该申请之前的所有历史记录
    """,
)
async def get_refund_details(
    refund_id: str,
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> RefundDetailsResponse:
    """获取退款申请详情API (T182)

    Args:
        refund_id: 退款申请ID
        token: JWT Token payload
        db: 数据库会话

    Returns:
        RefundDetailsResponse: 退款申请详情

    Raises:
        HTTPException 400: ID格式错误
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 404: 退款申请不存在
        HTTPException 500: 服务器内部错误
    """
    try:
        refund_service = FinanceRefundService(db)
        details = await refund_service.get_refund_details(refund_id)
        return details

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_REFUND_ID", "message": str(e)},
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "REFUND_NOT_FOUND", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取退款详情失败: {str(e)}",
            },
        )


@router.post(
    "/refunds/{refund_id}/approve",
    response_model=RefundApproveResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "请求参数错误或退款申请状态不允许审核"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
        404: {"description": "退款申请不存在"},
    },
    summary="批准退款申请",
    description="""
    批准退款申请,扣除运营商余额并创建退款交易记录。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **路径参数**:
    - refund_id: 退款申请ID(UUID格式)

    **请求体**:
    - note: 审核备注(可选,最多200字符)

    **响应数据**:
    - refund_id: 退款申请ID
    - requested_amount: 申请退款金额
    - actual_refund_amount: 实际退款金额(=当前余额)
    - balance_after: 退款后余额(=0.00)

    **业务规则**:
    - 仅能审核pending状态的申请
    - 实际退款金额 = 当前余额(全部退款)
    - 退款后余额归零
    - 创建退款类型交易记录
    - 记录审核人和审核时间
    - 若当前余额为0则无法批准
    """,
)
async def approve_refund(
    refund_id: str,
    request: RefundApproveRequest,
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> RefundApproveResponse:
    """批准退款申请API (T183)

    Args:
        refund_id: 退款申请ID
        request: 审核请求(包含可选的note)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        RefundApproveResponse: 审核结果

    Raises:
        HTTPException 400: ID格式错误或状态不允许审核或余额不足
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 404: 退款申请不存在
        HTTPException 500: 服务器内部错误
    """
    # 从token中提取finance_id
    finance_id_str = token.get("sub")
    if not finance_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Token中缺少财务ID"},
        )

    try:
        finance_id = UUID(finance_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FINANCE_ID",
                "message": f"无效的财务ID格式: {finance_id_str}",
            },
        )

    try:
        refund_service = FinanceRefundService(db)
        result = await refund_service.approve_refund(
            refund_id=refund_id, finance_id=finance_id, note=request.note
        )
        return result

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "APPROVAL_FAILED", "message": str(e)},
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "REFUND_NOT_FOUND", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"批准退款失败: {str(e)}",
            },
        )


@router.post(
    "/refunds/{refund_id}/reject",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "请求参数错误或退款申请状态不允许审核"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
        404: {"description": "退款申请不存在"},
    },
    summary="拒绝退款申请",
    description="""
    拒绝退款申请,不修改运营商余额。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **路径参数**:
    - refund_id: 退款申请ID(UUID格式)

    **请求体**:
    - reason: 拒绝原因(必填,10-200字符)

    **响应**:
    - 无响应体(HTTP 200)

    **业务规则**:
    - 仅能审核pending状态的申请
    - 必须提供拒绝原因
    - 不修改运营商余额
    - 不创建交易记录
    - 记录审核人、审核时间和拒绝原因
    """,
)
async def reject_refund(
    refund_id: str,
    request: RefundRejectRequest,
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """拒绝退款申请API (T184)

    Args:
        refund_id: 退款申请ID
        request: 拒绝请求(包含reason)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: 空dict(HTTP 200)

    Raises:
        HTTPException 400: ID格式错误或状态不允许审核或reason格式不正确
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 404: 退款申请不存在
        HTTPException 500: 服务器内部错误
    """
    # 从token中提取finance_id
    finance_id_str = token.get("sub")
    if not finance_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Token中缺少财务ID"},
        )

    try:
        finance_id = UUID(finance_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FINANCE_ID",
                "message": f"无效的财务ID格式: {finance_id_str}",
            },
        )

    try:
        refund_service = FinanceRefundService(db)
        await refund_service.reject_refund(
            refund_id=refund_id, finance_id=finance_id, reason=request.reason
        )
        return {}

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "REJECTION_FAILED", "message": str(e)},
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "REFUND_NOT_FOUND", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"拒绝退款失败: {str(e)}",
            },
        )


# ==================== 开票审核 (T185-T186) ====================


@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
    },
    summary="开票申请列表",
    description="""
    获取开票申请列表,支持分页和状态筛选。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **查询参数**:
    - status: 状态筛选(pending/approved/rejected/all,默认all)
    - page: 页码(从1开始,默认1)
    - page_size: 每页条数(1-100,默认20)

    **响应数据**:
    - page: 当前页码
    - page_size: 每页条数
    - total: 符合条件的总记录数
    - items: 开票申请列表(按申请时间倒序)
      - invoice_id: 开票申请ID
      - operator_id: 运营商ID
      - operator_name: 运营商名称
      - operator_category: 客户分类
      - amount: 开票金额
      - invoice_title: 发票抬头
      - tax_id: 纳税人识别号
      - email: 接收邮箱
      - status: 状态(pending/approved/rejected)
      - pdf_url: 发票PDF文件URL(已批准时)
      - reviewed_by: 审核人ID
      - reviewed_at: 审核时间
      - created_at: 申请创建时间

    **业务规则**:
    - 按申请时间倒序(最新申请在前)
    - PDF文件在批准后由后台异步生成
    """,
)
async def get_invoices(
    status: Optional[str] = Query("all", description="状态筛选(pending/approved/rejected/all)"),
    page: int = Query(1, ge=1, description="页码(从1开始)"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> InvoiceListResponse:
    """获取开票申请列表API (T185)

    Args:
        status: 状态筛选
        page: 页码
        page_size: 每页条数
        token: JWT Token payload
        db: 数据库会话

    Returns:
        InvoiceListResponse: 分页的开票申请列表

    Raises:
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 500: 服务器内部错误
    """
    try:
        invoice_service = FinanceInvoiceService(db)
        invoices = await invoice_service.get_invoices(
            status=status, page=page, page_size=page_size
        )
        return invoices

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取开票列表失败: {str(e)}",
            },
        )


@router.post(
    "/invoices/{invoice_id}/approve",
    response_model=InvoiceApproveResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "请求参数错误或开票申请状态不允许审核"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
        404: {"description": "开票申请不存在"},
    },
    summary="批准开票申请",
    description="""
    批准开票申请,生成发票编号和PDF文件URL。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **路径参数**:
    - invoice_id: 开票申请ID(UUID格式)

    **请求体**:
    - note: 审核备注(可选,最多200字符)

    **响应数据**:
    - invoice_id: 开票申请ID
    - pdf_url: 发票PDF文件URL

    **业务规则**:
    - 仅能审核pending状态的申请
    - 生成发票编号: INV-YYYYMMDD-XXXXX
    - 触发异步PDF生成任务(当前返回占位URL)
    - 记录审核人、审核时间和开票时间
    - PDF生成完成后会更新invoice_file_url
    """,
)
async def approve_invoice(
    invoice_id: str,
    request: InvoiceApproveRequest,
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> InvoiceApproveResponse:
    """批准开票申请API (T186)

    Args:
        invoice_id: 开票申请ID
        request: 审核请求(包含可选的note)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        InvoiceApproveResponse: 审核结果(包含PDF URL)

    Raises:
        HTTPException 400: ID格式错误或状态不允许审核
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 404: 开票申请不存在
        HTTPException 500: 服务器内部错误
    """
    # 从token中提取finance_id
    finance_id_str = token.get("sub")
    if not finance_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Token中缺少财务ID"},
        )

    try:
        finance_id = UUID(finance_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FINANCE_ID",
                "message": f"无效的财务ID格式: {finance_id_str}",
            },
        )

    try:
        invoice_service = FinanceInvoiceService(db)
        result = await invoice_service.approve_invoice(
            invoice_id=invoice_id, finance_id=finance_id, note=request.note
        )
        return result

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "APPROVAL_FAILED", "message": str(e)},
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "INVOICE_NOT_FOUND", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"批准开票失败: {str(e)}",
            },
        )


@router.post(
    "/invoices/{invoice_id}/reject",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "请求参数错误或开票申请状态不允许审核"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
        404: {"description": "开票申请不存在"},
    },
    summary="拒绝开票申请",
    description="""
    拒绝开票申请,不生成发票PDF。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **路径参数**:
    - invoice_id: 开票申请ID(UUID格式)

    **请求体**:
    - reason: 拒绝原因(必填,10-200字符)

    **响应**:
    - 无响应体(HTTP 200)

    **业务规则**:
    - 仅能审核pending状态的申请
    - 必须提供拒绝原因
    - 不生成发票编号和PDF
    - 记录审核人、审核时间和拒绝原因
    """,
)
async def reject_invoice(
    invoice_id: str,
    request: RefundRejectRequest,  # Reuse RefundRejectRequest as it has the same structure
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """拒绝开票申请API (T186续)

    Args:
        invoice_id: 开票申请ID
        request: 拒绝请求(包含reason)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: 空dict(HTTP 200)

    Raises:
        HTTPException 400: ID格式错误或状态不允许审核或reason格式不正确
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 404: 开票申请不存在
        HTTPException 500: 服务器内部错误
    """
    # 从token中提取finance_id
    finance_id_str = token.get("sub")
    if not finance_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Token中缺少财务ID"},
        )

    try:
        finance_id = UUID(finance_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FINANCE_ID",
                "message": f"无效的财务ID格式: {finance_id_str}",
            },
        )

    try:
        invoice_service = FinanceInvoiceService(db)
        await invoice_service.reject_invoice(
            invoice_id=invoice_id, finance_id=finance_id, reason=request.reason
        )
        return {}

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "REJECTION_FAILED", "message": str(e)},
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "INVOICE_NOT_FOUND", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"拒绝开票失败: {str(e)}",
            },
        )


# ==================== 审计日志 (T167) ====================


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
    },
    summary="获取审计日志列表",
    description="""
    获取财务操作审计日志列表,支持分页和筛选。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **查询参数**:
    - operation_type: 操作类型筛选(可选)
    - page: 页码(从1开始,默认1)
    - page_size: 每页条数(1-100,默认20)

    **响应数据**:
    - page: 当前页码
    - page_size: 每页条数
    - total: 符合条件的总记录数
    - items: 审计日志列表(按时间倒序)

    **业务规则**:
    - 按操作时间倒序(最新记录在前)
    - 记录所有财务人员的关键操作
    """,
)
async def get_audit_logs(
    operation_type: Optional[str] = Query(None, description="操作类型筛选"),
    page: int = Query(1, ge=1, description="页码(从1开始)"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """获取审计日志列表API (T167)

    Args:
        operation_type: 操作类型筛选
        page: 页码
        page_size: 每页条数
        token: JWT Token payload
        db: 数据库会话

    Returns:
        AuditLogListResponse: 分页的审计日志列表

    Raises:
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 500: 服务器内部错误
    """
    try:
        from sqlalchemy import select, func
        from ...models.finance import FinanceOperationLog, FinanceAccount
        from sqlalchemy.orm import selectinload

        # Build query
        query = select(FinanceOperationLog).options(
            selectinload(FinanceOperationLog.finance_account)
        )

        # Apply filters
        if operation_type:
            query = query.where(FinanceOperationLog.operation_type == operation_type)

        # Count total
        count_query = select(func.count()).select_from(FinanceOperationLog)
        if operation_type:
            count_query = count_query.where(FinanceOperationLog.operation_type == operation_type)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(FinanceOperationLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await db.execute(query)
        logs = result.scalars().all()

        # Build response
        from ...schemas.finance import AuditLogItem
        items = []
        for log in logs:
            items.append(AuditLogItem(
                log_id=f"log_{log.id}",
                finance_id=str(log.finance_account_id),
                finance_name=log.finance_account.full_name if log.finance_account else "Unknown",
                operation_type=log.operation_type,
                target_resource_id=str(log.target_resource_id) if log.target_resource_id else "",
                operation_details=log.operation_details or {},
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
            ))

        return AuditLogListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取审计日志失败: {str(e)}",
            },
        )


# ==================== 财务报表 (T166) ====================


@router.post(
    "/reports/generate",
    response_model=ReportGenerateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "请求参数错误"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
    },
    summary="生成财务报表",
    description="""
    生成财务报表(异步任务)。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **请求体**:
    - report_type: 报表类型(daily/weekly/monthly/custom)
    - start_date: 开始日期
    - end_date: 结束日期
    - format: 报表格式(pdf/excel)
    - include_sections: 包含的报表章节(可选)

    **响应数据**:
    - report_id: 报表ID
    - status: 生成状态(generating/completed/failed)
    - estimated_time: 预计完成时间(秒)

    **业务规则**:
    - 报表生成为异步任务
    - 可通过报表ID查询生成状态
    """,
)
async def generate_report(
    request: ReportGenerateRequest,
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> ReportGenerateResponse:
    """生成财务报表API (T166)

    Args:
        request: 报表生成请求
        token: JWT Token payload
        db: 数据库会话

    Returns:
        ReportGenerateResponse: 报表生成响应

    Raises:
        HTTPException 400: 请求参数错误
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 500: 服务器内部错误
    """
    try:
        # TODO: Implement actual report generation logic
        # For now, return a placeholder response
        import uuid
        from datetime import datetime

        report_id = f"rpt_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"

        return ReportGenerateResponse(
            report_id=report_id,
            status="completed",  # Immediately mark as completed for now
            estimated_time=0,
        )

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_REQUEST", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"生成报表失败: {str(e)}",
            },
        )


@router.get(
    "/reports",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
    },
    summary="获取报表历史列表",
    description="""
    获取历史生成的报表列表,支持分页。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **查询参数**:
    - page: 页码(从1开始,默认1)
    - page_size: 每页条数(1-100,默认20)

    **响应数据**:
    - page: 当前页码
    - page_size: 每页条数
    - total: 符合条件的总记录数
    - items: 报表列表(按创建时间倒序)

    **业务规则**:
    - 按创建时间倒序(最新报表在前)
    - 仅显示当前用户生成的报表
    """,
)
async def get_reports(
    page: int = Query(1, ge=1, description="页码(从1开始)"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    """获取报表历史列表API (T166)

    Args:
        page: 页码
        page_size: 每页条数
        token: JWT Token payload
        db: 数据库会话

    Returns:
        ReportListResponse: 分页的报表列表

    Raises:
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 500: 服务器内部错误
    """
    try:
        # TODO: Implement actual report list query
        # For now, return empty list
        return ReportListResponse(
            page=page,
            page_size=page_size,
            total=0,
            items=[],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取报表列表失败: {str(e)}",
            },
        )


@router.get(
    "/reports/{report_id}/export",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
        404: {"description": "报表不存在"},
    },
    summary="导出/下载报表文件",
    description="""
    导出指定报表的文件(PDF/Excel)。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **路径参数**:
    - report_id: 报表ID

    **响应**:
    - 文件流(application/pdf 或 application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)

    **业务规则**:
    - 仅允许下载已完成生成的报表
    - 文件名包含报表ID和日期
    """,
)
async def export_report(
    report_id: str,
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
):
    """导出报表文件API (T166)

    Args:
        report_id: 报表ID
        token: JWT Token payload
        db: 数据库会话

    Returns:
        FileResponse: 报表文件

    Raises:
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 404: 报表不存在
        HTTPException 500: 服务器内部错误
    """
    try:
        # TODO: Implement actual report export logic
        # For now, return 404
        raise NotFoundException(f"报表 {report_id} 不存在或尚未生成")

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "REPORT_NOT_FOUND", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"导出报表失败: {str(e)}",
            },
        )


# ==================== 运营商列表 ====================


@router.get(
    "/operators",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
    },
    summary="获取运营商列表",
    description="""
    获取运营商列表（用于手动充值时选择运营商）。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **查询参数**:
    - search: 搜索关键词（可选），支持用户名、姓名、邮箱、电话
    - status: 状态筛选（可选），active/inactive/locked
    - page: 页码，默认1
    - page_size: 每页条数，默认100（最大1000）

    **响应数据**:
    - items: 运营商列表
      - id: 运营商ID
      - username: 用户名
      - full_name: 真实姓名/公司名称
      - email: 邮箱
      - phone: 电话
      - balance: 当前余额
      - customer_tier: 客户分类
      - is_active: 是否激活
      - is_locked: 是否锁定
      - last_login_at: 最后登录时间
    - total: 总数量
    - page: 当前页码
    - page_size: 每页条数

    **业务规则**:
    - 只返回未删除的运营商
    - 支持关键词搜索和状态筛选
    - 默认按创建时间倒序排列
    """,
)
async def get_operators(
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="搜索关键词"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="状态筛选: active/inactive/locked"
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页条数"),
) -> dict:
    """获取运营商列表API

    Args:
        token: JWT Token payload
        db: 数据库会话
        search: 搜索关键词
        status_filter: 状态筛选
        page: 页码
        page_size: 每页条数

    Returns:
        dict: 运营商列表（分页）

    Raises:
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
    """
    from sqlalchemy import select, or_, func
    from ...models.operator import OperatorAccount

    # 🚀 性能优化: 构建WHERE条件列表,同时用于COUNT和数据查询
    # 原方案: 使用subquery包装完整查询再COUNT,需要执行两次复杂查询
    # 新方案: 复用WHERE条件,COUNT和SELECT分别执行,避免不必要的子查询
    conditions = [OperatorAccount.deleted_at.is_(None)]

    # 搜索条件
    if search:
        search_filter = or_(
            OperatorAccount.username.ilike(f"%{search}%"),
            OperatorAccount.full_name.ilike(f"%{search}%"),
            OperatorAccount.email.ilike(f"%{search}%"),
            OperatorAccount.phone.ilike(f"%{search}%"),
        )
        conditions.append(search_filter)

    # 状态筛选
    if status_filter == "active":
        conditions.extend([
            OperatorAccount.is_active == True,
            OperatorAccount.is_locked == False
        ])
    elif status_filter == "inactive":
        conditions.append(OperatorAccount.is_active == False)
    elif status_filter == "locked":
        conditions.append(OperatorAccount.is_locked == True)

    # 计算总数 - 使用相同条件直接COUNT
    count_query = select(func.count(OperatorAccount.id)).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 构建数据查询 - 使用相同条件
    query = select(OperatorAccount).where(*conditions)

    # 分页查询
    query = query.order_by(OperatorAccount.created_at.desc())
    query = query.limit(page_size).offset((page - 1) * page_size)

    result = await db.execute(query)
    operators = result.scalars().all()

    # 构建响应
    items = []
    for op in operators:
        items.append({
            "id": f"op_{op.id}",  # 添加前缀保持一致性
            "username": op.username,
            "full_name": op.full_name,
            "email": op.email,
            "phone": op.phone,
            "balance": float(op.balance),
            "customer_tier": op.customer_tier,
            "is_active": op.is_active,
            "is_locked": op.is_locked,
            "last_login_at": op.last_login_at.isoformat() if op.last_login_at else None,
            "created_at": op.created_at.isoformat() if op.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ==================== 手动充值 ====================


@router.post(
    "/recharge",
    response_model=RechargeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "请求参数错误或运营商不存在"},
        401: {"description": "未认证或Token无效/过期"},
        403: {"description": "权限不足(非财务人员)"},
        404: {"description": "运营商不存在"},
    },
    summary="手动充值",
    description="""
    财务人员为运营商手动充值。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: finance

    **请求体**:
    - operator_id: 运营商ID
    - amount: 充值金额（必须大于0）
    - description: 充值备注（可选）
    - payment_proof: 付款凭证文件（可选）

    **响应数据**:
    - transaction_id: 交易记录ID
    - operator_id: 运营商ID
    - operator_name: 运营商名称
    - amount: 充值金额
    - balance_before: 充值前余额
    - balance_after: 充值后余额
    - description: 充值备注
    - created_at: 充值时间

    **业务规则**:
    - 充值金额必须大于0
    - 更新运营商余额
    - 创建充值类型交易记录
    - 记录财务操作审计日志
    - 支持上传付款凭证文件
    """,
)
async def manual_recharge(
    operator_id: str = Form(...),
    amount: float = Form(..., gt=0),
    description: Optional[str] = Form(None),
    payment_proof: Optional[UploadFile] = File(None),
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> RechargeResponse:
    """手动充值API

    Args:
        operator_id: 运营商ID
        amount: 充值金额
        description: 充值备注
        payment_proof: 付款凭证文件
        token: JWT Token payload
        db: 数据库会话

    Returns:
        RechargeResponse: 充值结果

    Raises:
        HTTPException 400: 请求参数错误
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
        HTTPException 500: 服务器内部错误
    """
    # 从token中提取finance_id
    finance_id_str = token.get("sub")
    if not finance_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Token中缺少财务ID"},
        )

    try:
        from uuid import UUID
        finance_id = UUID(finance_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FINANCE_ID",
                "message": f"无效的财务ID格式: {finance_id_str}",
            },
        )

    try:
        from datetime import datetime
        from decimal import Decimal
        from sqlalchemy import select
        from ...models.operator import OperatorAccount
        from ...models.transaction import TransactionRecord
        from ...models.finance import FinanceOperationLog

        # 解析运营商ID（移除 "op_" 前缀）
        actual_operator_id = operator_id.replace("op_", "") if operator_id.startswith("op_") else operator_id

        try:
            operator_uuid = UUID(actual_operator_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_OPERATOR_ID",
                    "message": f"无效的运营商ID格式: {operator_id}",
                },
            )

        # 查询运营商（使用行级锁防止并发问题）
        query = select(OperatorAccount).where(
            OperatorAccount.id == operator_uuid,
            OperatorAccount.deleted_at.is_(None)
        ).with_for_update()

        result = await db.execute(query)
        operator = result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "OPERATOR_NOT_FOUND", "message": "运营商不存在或已删除"},
            )

        # 验证运营商状态
        if not operator.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "OPERATOR_INACTIVE", "message": "运营商账户已停用"},
            )

        if operator.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "OPERATOR_LOCKED", "message": "运营商账户已锁定"},
            )

        # 记录充值前余额
        balance_before = operator.balance
        recharge_amount = Decimal(str(amount))

        # 更新运营商余额
        operator.balance = operator.balance + recharge_amount
        balance_after = operator.balance

        # 处理付款凭证文件（如果有）
        payment_proof_path = None
        if payment_proof:
            import os
            upload_dir = "uploads/payment_proofs"
            os.makedirs(upload_dir, exist_ok=True)
            file_extension = payment_proof.filename.split('.')[-1] if payment_proof.filename else 'jpg'
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{actual_operator_id}.{file_extension}"
            file_path = os.path.join(upload_dir, filename)

            # 🚀 性能优化: 使用异步文件I/O,避免阻塞事件循环
            # 原方案: 同步写入文件,阻塞整个事件循环
            # 新方案: 异步写入文件,不阻塞其他请求
            content = await payment_proof.read()
            import aiofiles
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)

            payment_proof_path = file_path

        # 创建交易记录（手动充值不需要设置payment_channel等字段）
        transaction = TransactionRecord(
            operator_id=operator_uuid,
            transaction_type="recharge",
            amount=recharge_amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description or "财务手动充值",
        )
        db.add(transaction)

        # 记录财务操作日志
        operation_log = FinanceOperationLog(
            finance_account_id=finance_id,
            operation_type="manual_recharge",
            target_resource_type="operator",
            target_resource_id=operator_uuid,
            operation_details={
                "operator_id": str(operator_uuid),
                "operator_username": operator.username,
                "operator_name": operator.full_name,
                "amount": str(recharge_amount),
                "balance_before": str(balance_before),
                "balance_after": str(balance_after),
                "description": description,
                "payment_proof": payment_proof_path,
            },
            ip_address="127.0.0.1",  # TODO: 从请求中获取真实IP
        )
        db.add(operation_log)

        # 提交事务
        await db.commit()
        await db.refresh(transaction)

        # 返回充值结果
        return RechargeResponse(
            transaction_id=f"txn_{transaction.id}",
            operator_id=f"op_{operator_uuid}",
            operator_name=operator.full_name,
            amount=f"{recharge_amount:.2f}",
            balance_before=f"{balance_before:.2f}",
            balance_after=f"{balance_after:.2f}",
            description=description or "财务手动充值",
            created_at=transaction.created_at,
        )

    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "RECHARGE_FAILED", "message": str(e)},
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "OPERATOR_NOT_FOUND", "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"充值失败: {str(e)}",
            },
        )


@router.get(
    "/recharge-records",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="获取充值记录列表",
    description="财务人员查询所有运营商的充值记录，支持筛选和分页",
)
async def get_recharge_records(
    operator_id: Optional[str] = Query(None, description="运营商ID筛选（格式: op_xxx或uuid）"),
    start_date: Optional[str] = Query(None, description="开始日期（格式: YYYY-MM-DD）"),
    end_date: Optional[str] = Query(None, description="结束日期（格式: YYYY-MM-DD）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取充值记录列表

    返回所有运营商的充值记录，包括：
    - 手动充值（财务操作）
    - 在线充值（支付宝/微信支付）

    支持按运营商、日期范围筛选，按时间倒序排列
    """
    from datetime import datetime
    from sqlalchemy import select, and_, func
    from sqlalchemy.orm import selectinload
    from ...models.transaction import TransactionRecord
    from ...models.operator import OperatorAccount

    try:
        # 构建基础查询 - 只查询充值类型的交易
        query = select(TransactionRecord).where(
            TransactionRecord.transaction_type == "recharge"
        ).options(
            selectinload(TransactionRecord.operator)
        )

        # 筛选条件
        filters = []

        # 按运营商筛选
        if operator_id:
            # 解析运营商ID（移除op_前缀）
            actual_operator_id = operator_id.replace("op_", "") if operator_id.startswith("op_") else operator_id
            try:
                operator_uuid = UUID(actual_operator_id)
                filters.append(TransactionRecord.operator_id == operator_uuid)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error_code": "INVALID_OPERATOR_ID", "message": "无效的运营商ID格式"}
                )

        # 按日期范围筛选
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                filters.append(TransactionRecord.created_at >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error_code": "INVALID_DATE", "message": "开始日期格式错误，应为YYYY-MM-DD"}
                )

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                # 结束日期包含当天23:59:59
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                filters.append(TransactionRecord.created_at <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error_code": "INVALID_DATE", "message": "结束日期格式错误，应为YYYY-MM-DD"}
                )

        # 应用筛选条件
        if filters:
            query = query.where(and_(*filters))

        # 按时间倒序排列
        query = query.order_by(TransactionRecord.created_at.desc())

        # 统计总数
        count_query = select(func.count()).select_from(TransactionRecord).where(
            TransactionRecord.transaction_type == "recharge"
        )
        if filters:
            count_query = count_query.where(and_(*filters))

        result = await db.execute(count_query)
        total = result.scalar()

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # 执行查询
        result = await db.execute(query)
        records = result.scalars().all()

        # 构建响应数据
        items = []
        for record in records:
            # 判断充值方式
            if record.payment_channel:
                recharge_method = "在线充值"
                payment_info = {
                    "channel": record.payment_channel,
                    "order_no": record.payment_order_no,
                    "status": record.payment_status,
                }
            else:
                recharge_method = "手动充值"
                payment_info = None

            items.append({
                "id": f"txn_{record.id}",
                "transaction_id": str(record.id),
                "operator_id": f"op_{record.operator_id}",
                "operator_username": record.operator.username,
                "operator_name": record.operator.full_name,
                "amount": f"{record.amount:.2f}",
                "balance_before": f"{record.balance_before:.2f}",
                "balance_after": f"{record.balance_after:.2f}",
                "recharge_method": recharge_method,
                "payment_info": payment_info,
                "description": record.description or "",
                "created_at": record.created_at.isoformat(),
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"查询充值记录失败: {str(e)}",
            },
        )
