"""充值相关Pydantic schemas (T059)

定义充值申请请求和响应的数据结构。

契约基础: specs/001-mr/contracts/operator.yaml
- POST /operators/me/recharge: 发起充值
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


class RechargeRequest(BaseModel):
    """充值请求 (POST /operators/me/recharge)

    契约要求:
    - amount: 充值金额(最小10元,最大10000元)
    - payment_method: 支付方式(wechat/alipay)
    """

    amount: str = Field(
        ...,
        description="充值金额(最小10元,最大10000元)",
        examples=["500.00"],
        pattern=r'^\d+(\.\d{1,2})?$'
    )

    payment_method: Literal["wechat", "alipay"] = Field(
        ...,
        description="支付方式: wechat(微信支付)/alipay(支付宝)",
        examples=["wechat"]
    )

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: str) -> str:
        """验证充值金额范围"""
        try:
            amount_decimal = Decimal(v)
        except Exception:
            raise ValueError("充值金额格式错误")

        if amount_decimal < Decimal("10.00"):
            raise ValueError("充值金额不能低于10元")

        if amount_decimal > Decimal("10000.00"):
            raise ValueError("充值金额不能超过10000元")

        # 验证小数位数不超过2位
        if amount_decimal.as_tuple().exponent < -2:
            raise ValueError("充值金额最多2位小数")

        return v


class RechargeResponse(BaseModel):
    """充值订单响应 (RechargeOrder schema)

    契约定义: operator.yaml#/components/schemas/RechargeOrder
    """

    order_id: str = Field(
        ...,
        description="充值订单ID",
        examples=["ord_recharge_20250115_123456"]
    )

    amount: str = Field(
        ...,
        description="充值金额",
        examples=["500.00"]
    )

    payment_method: str = Field(
        ...,
        description="支付方式: wechat/alipay",
        examples=["wechat"]
    )

    qr_code_url: str = Field(
        ...,
        description="支付二维码URL",
        examples=["https://payment.example.com/qr/abc123"]
    )

    payment_url: Optional[str] = Field(
        None,
        description="支付页面URL(H5场景)",
        examples=["https://payment.example.com/pay/abc123"]
    )

    expires_at: datetime = Field(
        ...,
        description="订单过期时间(30分钟有效期)",
        examples=["2025-01-15T13:00:00.000Z"]
    )

    class Config:
        from_attributes = True


class PaymentCallbackRequest(BaseModel):
    """支付回调请求 (POST /webhooks/payment/{wechat|alipay})

    支付平台回调时的请求体。
    """

    order_id: str = Field(
        ...,
        description="充值订单ID",
        examples=["ord_recharge_20250115_123456"]
    )

    status: Literal["success", "failed"] = Field(
        ...,
        description="支付状态",
        examples=["success"]
    )

    paid_amount: str = Field(
        ...,
        description="实际支付金额",
        examples=["500.00"],
        pattern=r'^\d+(\.\d{1,2})?$'
    )

    transaction_id: str = Field(
        ...,
        description="支付平台交易ID",
        examples=["wxpay_txn_abc123"]
    )

    paid_at: datetime = Field(
        ...,
        description="支付完成时间",
        examples=["2025-01-15T12:35:00.000Z"]
    )

    error_code: Optional[str] = Field(
        None,
        description="错误码(status=failed时)",
        examples=["USER_CANCEL"]
    )

    error_message: Optional[str] = Field(
        None,
        description="错误信息(status=failed时)",
        examples=["用户取消支付"]
    )


class PaymentCallbackResponse(BaseModel):
    """支付回调响应

    返回给支付平台的确认响应。
    """

    success: bool = Field(
        ...,
        description="处理成功标志",
        examples=[True]
    )

    message: str = Field(
        ...,
        description="处理结果消息",
        examples=["Payment callback processed successfully"]
    )
