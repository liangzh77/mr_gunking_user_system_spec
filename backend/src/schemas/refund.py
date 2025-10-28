"""退款相关Pydantic schemas (T060)

定义退款申请请求和响应的数据结构。

契约基础: specs/001-mr/contracts/operator.yaml
- POST /operators/me/refunds: 申请退款
- GET /operators/me/refunds: 查询退款列表
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RefundRequestCreate(BaseModel):
    """退款申请请求 (POST /operators/me/refunds)

    契约要求:
    - reason: 退款原因,10-500字符
    """

    reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="退款原因",
        examples=["业务调整,不再继续使用服务"]
    )

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v: str) -> str:
        """验证退款原因不能为空白字符"""
        if not v.strip():
            raise ValueError("退款原因不能为空白字符")
        return v.strip()


class RefundRequestResponse(BaseModel):
    """退款申请响应 (RefundRequest schema)

    契约定义: operator.yaml#/components/schemas/RefundRequest
    """

    refund_id: str = Field(
        ...,
        description="退款申请ID",
        examples=["refund_20250115_001"]
    )

    requested_amount: str = Field(
        ...,
        description="申请退款金额(申请时余额)",
        examples=["100.00"]
    )

    actual_refund_amount: Optional[str] = Field(
        None,
        description="实际退款金额(审核时余额,可能小于申请金额)",
        examples=["80.00"]
    )

    status: str = Field(
        ...,
        description="审核状态: pending/approved/rejected",
        examples=["pending"]
    )

    reason: str = Field(
        ...,
        description="退款原因",
        examples=["业务调整,不再继续使用"]
    )

    reject_reason: Optional[str] = Field(
        None,
        description="拒绝原因(status=rejected时)",
        examples=["退款原因不充分"]
    )

    reviewed_by: Optional[str] = Field(
        None,
        description="审核人ID",
        examples=["fin_001"]
    )

    reviewed_at: Optional[datetime] = Field(
        None,
        description="审核时间",
        examples=["2025-01-16T10:00:00.000Z"]
    )

    created_at: datetime = Field(
        ...,
        description="申请时间",
        examples=["2025-01-15T16:00:00.000Z"]
    )

    class Config:
        from_attributes = True  # 允许从ORM模型转换
