# 财务人员银行转账审核API
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from ...db.session import get_db
from ...models.bank_transfer import BankTransferApplication
from ...models.finance import FinanceAccount
from ...models.operator import OperatorAccount
from ...schemas.finance.bank_transfer import (
    BankTransferListResponse,
    BankTransferListRequest,
    BankTransferItem,
    ApproveBankTransferRequest,
    RejectBankTransferRequest,
    BankTransferStatus
)
from ...services.bank_transfer_service import BankTransferService
from ...api.dependencies import get_db, require_finance

router = APIRouter(prefix="/bank-transfers", tags=["财务-银行转账审核"])


@router.get(
    "",
    response_model=BankTransferListResponse,
    status_code=status.HTTP_200_OK,
    summary="查询银行转账充值申请列表",
    description="财务人员查询所有运营商的银行转账充值申请列表"
)
async def get_bank_transfers(
    status: Optional[str] = Query(None, description="申请状态筛选: pending/approved/rejected/cancelled"),
    search: Optional[str] = Query(None, description="搜索关键词: 运营商名称/用户名/申请ID"),
    operator_id: Optional[str] = Query(None, description="运营商ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
) -> BankTransferListResponse:
    """查询银行转账充值申请列表API

    Args:
        status: 状态筛选
        search: 搜索关键词
        operator_id: 运营商ID筛选
        page: 页码
        page_size: 每页条数
        start_date: 开始日期
        end_date: 结束日期
        token: JWT Token payload
        db: 数据库会话

    Returns:
        BankTransferListResponse: 申请列表
    """
    # 验证状态参数
    if status:
        valid_statuses = ["pending", "approved", "rejected", "cancelled"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error_code": "INVALID_STATUS", "message": f"无效的状态值，必须是: {', '.join(valid_statuses)}"}
            )

    # 调用服务层查询列表
    transfer_service = BankTransferService(db)
    try:
        return await transfer_service.get_applications_for_finance(
            status=status,
            search=search,
            operator_id=operator_id,
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": f"查询申请列表失败: {str(e)}"}
        )


@router.post(
    "/{transfer_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="批准银行转账充值申请",
    description="财务人员批准待审核的银行转账充值申请"
)
async def approve_bank_transfer(
    transfer_id: str,
    request: ApproveBankTransferRequest,
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """批准银行转账充值申请API

    Args:
        transfer_id: 申请ID (UUID)
        request: 批准请求
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: 操作结果
    """
    # 解析transfer_id
    try:
        transfer_uuid = UUID(transfer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "INVALID_TRANSFER_ID", "message": f"无效的申请ID格式: {transfer_id}"}
        )

    # 获取财务人员ID
    finance_id_str = token.get("sub")
    if not finance_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Token中缺少财务人员ID"}
        )

    try:
        finance_id = UUID(finance_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_FINANCE_ID", "message": f"无效的财务人员ID格式: {finance_id_str}"}
        )

    # 调用服务层批准申请
    transfer_service = BankTransferService(db)
    try:
        result = await transfer_service.approve_application(
            transfer_uuid=transfer_uuid,
            reviewer_id=finance_id
        )
        return {
            "application_id": str(result.id),
            "status": result.status,
            "reviewed_at": result.reviewed_at,
            "message": "银行转账申请已批准"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": f"批准申请失败: {str(e)}"}
        )


@router.post(
    "/{transfer_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="拒绝银行转账充值申请",
    description="财务人员拒绝待审核的银行转账充值申请"
)
async def reject_bank_transfer(
    transfer_id: str,
    request: RejectBankTransferRequest,
    token: dict = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """拒绝银行转账充值申请API

    Args:
        transfer_id: 申请ID (UUID)
        request: 拒绝请求
        token: JWT Token payload
        db: 数据库会话

    Returns:
        dict: 操作结果
    """
    # 验证拒绝原因
    if not request.reject_reason or len(request.reject_reason.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "EMPTY_REASON", "message": "拒绝原因不能为空"}
        )

    if len(request.reject_reason) > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "REASON_TOO_LONG", "message": "拒绝原因不能超过500个字符"}
        )

    # 解析transfer_id
    try:
        transfer_uuid = UUID(transfer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "INVALID_TRANSFER_ID", "message": f"无效的申请ID格式: {transfer_id}"}
        )

    # 获取财务人员ID
    finance_id_str = token.get("sub")
    if not finance_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Token中缺少财务人员ID"}
        )

    try:
        finance_id = UUID(finance_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_FINANCE_ID", "message": f"无效的财务人员ID格式: {finance_id_str}"}
        )

    # 调用服务层拒绝申请
    transfer_service = BankTransferService(db)
    try:
        result = await transfer_service.reject_application(
            transfer_uuid=transfer_uuid,
            reviewer_id=finance_id,
            reject_reason=request.reject_reason.strip()
        )
        return {
            "application_id": str(result.id),
            "status": result.status,
            "reject_reason": result.reject_reason,
            "reviewed_at": result.reviewed_at,
            "message": "银行转账申请已拒绝"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": f"拒绝申请失败: {str(e)}"}
        )