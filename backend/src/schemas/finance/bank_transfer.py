# 银行转账审核Schema
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class BankTransferStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class BankTransferItem(BaseModel):
    """银行转账申请项"""
    application_id: str = Field(..., description="申请ID")
    operator_id: str = Field(..., description="运营商ID")
    operator_name: str = Field(..., description="运营商名称")
    operator_username: str = Field(..., description="运营商用户名")
    amount: float = Field(..., description="充值金额")
    voucher_image_url: str = Field(..., description="转账凭证图片URL")
    remark: Optional[str] = Field(None, description="备注")
    status: BankTransferStatus = Field(..., description="申请状态")
    reject_reason: Optional[str] = Field(None, description="拒绝原因")
    created_at: datetime = Field(..., description="申请时间")
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    reviewed_by: Optional[str] = Field(None, description="审核人员")

    class Config:
        from_attributes = True


class BankTransferListRequest(BaseModel):
    """银行转账列表查询请求"""
    status: Optional[str] = Field(None, description="状态筛选")
    search: Optional[str] = Field(None, description="搜索关键词(运营商/申请ID)")
    operator_id: Optional[str] = Field(None, description="运营商ID筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
    start_date: Optional[str] = Field(None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期 YYYY-MM-DD")


class BankTransferListResponse(BaseModel):
    """银行转账列表响应"""
    items: List[BankTransferItem] = Field(..., description="转账申请列表")
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")


class BankTransferDetailResponse(BankTransferItem):
    """银行转账详情响应"""
    bank_account_name: str = Field(..., description="收款账户名")
    bank_account_number: str = Field(..., description="收款账号")
    bank_name: str = Field(..., description="收款银行")
    reviewer_name: Optional[str] = Field(None, description="审核人员姓名")


class ApproveBankTransferRequest(BaseModel):
    """批准银行转账请求"""
    pass  # 批准无需额外参数


class RejectBankTransferRequest(BaseModel):
    """拒绝银行转账请求"""
    reject_reason: str = Field(..., min_length=1, max_length=500, description="拒绝原因")


class BankTransferStatisticsResponse(BaseModel):
    """银行转账统计响应"""
    total_count: int = Field(..., description="总申请数")
    pending_count: int = Field(..., description="待审核数")
    approved_count: int = Field(..., description="已批准数")
    rejected_count: int = Field(..., description="已拒绝数")
    cancelled_count: int = Field(..., description="已取消数")
    total_amount: float = Field(..., description="总申请金额")
    approved_amount: float = Field(..., description="已批准金额")