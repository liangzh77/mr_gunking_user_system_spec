"""交易记录相关的Pydantic Schemas (T043)

此模块定义交易记录(TransactionRecord)的数据模型。
用于API响应和数据序列化。

交易类型:
- recharge: 充值(amount为正)
- consumption: 消费(amount为负)
- refund: 退款(amount为正)
"""

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


class TransactionRecordBase(BaseModel):
    """交易记录基础模型"""

    transaction_type: Literal["recharge", "consumption", "refund"] = Field(
        ...,
        description="交易类型: recharge/consumption/refund",
        examples=["consumption"]
    )

    amount: str = Field(
        ...,
        description="交易金额(充值和退款为正,消费为负)",
        pattern=r'^-?\d+\.\d{2}$',
        examples=["-50.00"]
    )

    balance_before: str = Field(
        ...,
        description="交易前余额",
        pattern=r'^\d+\.\d{2}$',
        examples=["5330.50"]
    )

    balance_after: str = Field(
        ...,
        description="交易后余额",
        pattern=r'^\d+\.\d{2}$',
        examples=["5280.50"]
    )

    description: Optional[str] = Field(
        None,
        description="交易描述",
        examples=["游戏消费：太空探险 - 5人 - 北京朝阳门店"]
    )

    @field_validator('amount', 'balance_before', 'balance_after')
    @classmethod
    def validate_decimal_format(cls, v: str) -> str:
        """验证金额格式"""
        try:
            decimal_value = Decimal(v)
            # amount可以为负数,其他必须非负
            return v
        except Exception:
            raise ValueError(f"金额格式错误: {v}")


class TransactionRecordCreate(TransactionRecordBase):
    """创建交易记录的请求模型

    内部使用,不对外暴露
    """

    operator_id: UUID
    related_usage_id: Optional[UUID] = None
    related_refund_id: Optional[UUID] = None
    payment_channel: Optional[Literal["wechat", "alipay"]] = None
    payment_order_no: Optional[str] = None
    payment_status: Optional[Literal["pending", "success", "failed"]] = None
    payment_callback_at: Optional[datetime] = None


class TransactionRecordInDB(TransactionRecordBase):
    """数据库中的交易记录完整模型"""

    id: UUID = Field(..., description="交易记录ID")
    operator_id: UUID = Field(..., description="运营商ID")
    related_usage_id: Optional[UUID] = Field(None, description="关联使用记录ID")
    related_refund_id: Optional[UUID] = Field(None, description="关联退款记录ID")
    payment_channel: Optional[str] = Field(None, description="支付渠道")
    payment_order_no: Optional[str] = Field(None, description="支付平台订单号")
    payment_status: Optional[str] = Field(None, description="支付状态")
    payment_callback_at: Optional[datetime] = Field(None, description="支付回调时间")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class TransactionRecordResponse(TransactionRecordBase):
    """交易记录响应模型(对外API)"""

    id: UUID = Field(..., description="交易记录ID")
    payment_channel: Optional[str] = Field(None, description="支付渠道")
    payment_order_no: Optional[str] = Field(None, description="支付平台订单号")
    payment_status: Optional[str] = Field(None, description="支付状态")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "cc0e8400-e29b-41d4-a716-446655440007",
                "transaction_type": "consumption",
                "amount": "-50.00",
                "balance_before": "5330.50",
                "balance_after": "5280.50",
                "description": "游戏消费：太空探险 - 5人 - 北京朝阳门店",
                "payment_channel": None,
                "payment_order_no": None,
                "payment_status": None,
                "created_at": "2025-10-10T14:30:00+08:00"
            }
        }


class RechargeRequest(BaseModel):
    """充值请求模型(用于后续User Story)"""

    amount: str = Field(
        ...,
        description="充值金额",
        pattern=r'^\d+\.\d{2}$',
        examples=["100.00"]
    )

    payment_channel: Literal["wechat", "alipay"] = Field(
        ...,
        description="支付渠道",
        examples=["wechat"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "amount": "100.00",
                "payment_channel": "wechat"
            }
        }
