"""
银行转账相关的Pydantic Schemas (运营商端)

包含:
- 银行转账充值申请和响应schemas
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BankAccountInfo(BaseModel):
    """银行账户信息"""
    bank_name: str = Field(..., description="收款银行")
    account_number: str = Field(..., description="收款账号")
    account_name: str = Field(..., description="收款账户名")

    class Config:
        from_attributes = True


class BankTransferCreate(BaseModel):
    """创建银行转账申请请求"""
    amount: float = Field(..., gt=0, description="充值金额")
    voucher_image_url: str = Field(..., description="转账凭证图片URL")
    remark: Optional[str] = Field(None, max_length=500, description="备注")
    payment_method: Optional[str] = Field('bank_transfer', description="支付方式: bank_transfer或wechat")

    class Config:
        from_attributes = True


class BankTransferResponse(BaseModel):
    """银行转账申请响应"""
    id: str = Field(..., description="记录ID")
    application_id: str = Field(..., description="申请ID")
    operator_id: str = Field(..., description="运营商ID")
    amount: float = Field(..., description="充值金额")
    voucher_image_url: str = Field(..., description="转账凭证图片URL")
    remark: Optional[str] = Field(None, description="备注")
    payment_method: Optional[str] = Field('bank_transfer', description="支付方式")
    status: str = Field(..., description="申请状态")
    reject_reason: Optional[str] = Field(None, description="拒绝原因")
    created_at: datetime = Field(..., description="申请时间")
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    reviewed_by: Optional[str] = Field(None, description="审核人员")

    class Config:
        from_attributes = True


class BankTransferListResponse(BaseModel):
    """银行转账申请列表响应"""
    items: list[BankTransferResponse] = Field(..., description="转账申请列表")
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")

    class Config:
        from_attributes = True