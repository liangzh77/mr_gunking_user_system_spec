"""发票相关Pydantic schemas (T061)

定义发票申请请求和响应的数据结构。

契约基础: specs/001-mr/contracts/operator.yaml
- POST /operators/me/invoices: 申请开具发票
- GET /operators/me/invoices: 查询发票列表
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class InvoiceRequestCreate(BaseModel):
    """发票申请请求 (POST /operators/me/invoices)

    契约要求:
    - amount: 开票金额(不能超过已充值金额)
    - invoice_title: 发票抬头
    - tax_id: 纳税人识别号,15-20位字母数字
    - email: 接收邮箱(可选)
    """

    amount: str = Field(
        ...,
        description="开票金额(不能超过已充值金额)",
        examples=["1000.00"],
        pattern=r'^\d+(\.\d{1,2})?$'
    )

    invoice_title: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="发票抬头",
        examples=["北京星空娱乐有限公司"]
    )

    tax_id: str = Field(
        ...,
        description="纳税人识别号(15-20位字母数字)",
        examples=["91110000123456789X"],
        pattern=r'^[A-Z0-9]{15,20}$'
    )

    email: Optional[EmailStr] = Field(
        None,
        description="接收发票的邮箱(可选,默认使用账户邮箱)",
        examples=["finance@example.com"]
    )

    @field_validator('invoice_title')
    @classmethod
    def validate_invoice_title(cls, v: str) -> str:
        """验证发票抬头不能为空白字符"""
        if not v.strip():
            raise ValueError("发票抬头不能为空白字符")
        return v.strip()

    @field_validator('tax_id')
    @classmethod
    def validate_tax_id(cls, v: str) -> str:
        """验证税号为大写字母数字"""
        v = v.upper().strip()
        if len(v) < 15 or len(v) > 20:
            raise ValueError("纳税人识别号长度必须在15-20位之间")
        if not v.isalnum():
            raise ValueError("纳税人识别号只能包含字母和数字")
        return v


class InvoiceResponse(BaseModel):
    """发票申请响应 (Invoice schema)

    契约定义: operator.yaml#/components/schemas/Invoice
    """

    invoice_id: str = Field(
        ...,
        description="发票ID",
        examples=["inv_20250115_001"]
    )

    amount: str = Field(
        ...,
        description="开票金额",
        examples=["1000.00"]
    )

    invoice_title: str = Field(
        ...,
        description="发票抬头",
        examples=["北京星空娱乐有限公司"]
    )

    invoice_type: Optional[str] = Field(
        None,
        description="发票类型: vat_normal/vat_special",
        examples=["vat_normal"]
    )

    tax_id: str = Field(
        ...,
        description="纳税人识别号",
        examples=["91110000123456789X"]
    )

    email: Optional[str] = Field(
        None,
        description="接收邮箱",
        examples=["finance@example.com"]
    )

    status: str = Field(
        ...,
        description="审核状态: pending/approved/rejected/issued",
        examples=["pending"]
    )

    reject_reason: Optional[str] = Field(
        None,
        description="拒绝原因(status=rejected时)",
        examples=[None]
    )

    invoice_number: Optional[str] = Field(
        None,
        description="发票号码",
        examples=[None]
    )

    pdf_url: Optional[str] = Field(
        None,
        description="发票PDF下载链接(status=approved时)",
        examples=["https://api.example.com/invoices/inv_20250115_001.pdf"]
    )

    reviewed_by: Optional[str] = Field(
        None,
        description="审核人ID",
        examples=["fin_001"]
    )

    reviewed_at: Optional[datetime] = Field(
        None,
        description="审核时间",
        examples=["2025-01-16T11:00:00.000Z"]
    )

    created_at: datetime = Field(
        ...,
        description="申请时间",
        examples=["2025-01-15T17:00:00.000Z"]
    )

    class Config:
        from_attributes = True  # 允许从ORM模型转换
