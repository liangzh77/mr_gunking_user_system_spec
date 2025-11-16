"""银行转账充值相关Pydantic schemas

定义银行转账充值申请请求和响应的数据结构。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BankTransferCreate(BaseModel):
    """银行转账充值申请请求 (POST /operators/me/bank-transfers)

    字段要求:
    - amount: 申请充值金额,必须大于0
    - voucher_image_url: 转账凭证图片URL,必填
    - remark: 申请备注,可选,最多500字符
    """

    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="申请充值金额",
        examples=["100.00", "500.50"]
    )

    voucher_image_url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="转账凭证图片URL",
        examples=["https://example.com/vouchers/20251113_abc123.jpg"]
    )

    remark: Optional[str] = Field(
        None,
        max_length=500,
        description="申请备注(可选)",
        examples=["转账时间2025-11-13 14:00"]
    )

    @field_validator('remark')
    @classmethod
    def validate_remark(cls, v: Optional[str]) -> Optional[str]:
        """验证备注不能为空白字符"""
        if v is not None and not v.strip():
            raise ValueError("备注不能为空白字符")
        return v.strip() if v else None


class BankTransferResponse(BaseModel):
    """银行转账充值申请响应

    返回申请的详细信息,包括审核状态
    """

    id: str = Field(
        ...,
        description="申请UUID(用于API调用)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    application_id: str = Field(
        ...,
        description="申请ID (格式: BTR_YYYYMMDD_XXXXX)",
        examples=["BTR_20251113_ABC12"]
    )

    operator_id: str = Field(
        ...,
        description="运营商ID",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    amount: str = Field(
        ...,
        description="申请充值金额",
        examples=["100.00"]
    )

    voucher_image_url: str = Field(
        ...,
        description="转账凭证图片URL",
        examples=["https://example.com/vouchers/20251113_abc123.jpg"]
    )

    remark: Optional[str] = Field(
        None,
        description="申请备注",
        examples=["转账时间2025-11-13 14:00"]
    )

    status: str = Field(
        ...,
        description="审核状态: pending/approved/rejected",
        examples=["pending"]
    )

    reject_reason: Optional[str] = Field(
        None,
        description="拒绝原因(status=rejected时)",
        examples=["转账凭证不清晰"]
    )

    reviewed_by: Optional[str] = Field(
        None,
        description="审核人ID(财务人员)",
        examples=["fin_001"]
    )

    reviewed_at: Optional[datetime] = Field(
        None,
        description="审核时间",
        examples=["2025-11-13T15:00:00.000Z"]
    )

    created_at: datetime = Field(
        ...,
        description="申请时间",
        examples=["2025-11-13T14:00:00.000Z"]
    )

    updated_at: datetime = Field(
        ...,
        description="更新时间",
        examples=["2025-11-13T14:00:00.000Z"]
    )

    class Config:
        from_attributes = True  # 允许从ORM模型转换


class BankTransferListResponse(BaseModel):
    """银行转账充值申请列表响应"""

    page: int = Field(..., description="当前页码", examples=[1])
    page_size: int = Field(..., description="每页条数", examples=[20])
    total: int = Field(..., description="总条数", examples=[100])
    items: list[BankTransferResponse] = Field(
        ...,
        description="申请列表"
    )


class BankAccountInfo(BaseModel):
    """银行账户信息响应

    返回公司银行账户信息,用于前端显示
    """

    account_name: str = Field(
        ...,
        description="开户名称",
        examples=["北京触角科技有限公司"]
    )

    account_number: str = Field(
        ...,
        description="银行账号",
        examples=["0106014170032120"]
    )

    bank_name: str = Field(
        ...,
        description="开户银行",
        examples=["民生银行北京工体北路支行"]
    )
