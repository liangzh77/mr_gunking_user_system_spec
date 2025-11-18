"""交易记录模型 (TransactionRecord)

此模型对应 data-model.md 中的 transaction_records 表。
记录所有资金流动(充值和消费),用于财务审计和对账。

关键特性:
- 交易类型: recharge/consumption/refund
- 余额快照(before/after)确保审计完整性
- 关联使用记录(消费类型)
- 支付渠道和状态管理(充值类型)
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID as PyUUID, uuid4

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    DECIMAL,
    TIMESTAMP,
    text,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class TransactionType(str, Enum):
    """交易类型枚举"""
    RECHARGE = "recharge"      # 充值
    CONSUMPTION = "consumption"  # 消费
    REFUND = "refund"          # 退款


class TransactionStatus(str, Enum):
    """交易/订单状态枚举"""
    PENDING = "pending"        # 待支付/处理中
    PROCESSING = "processing"  # 处理中(用于支付对账)
    SUCCESS = "success"        # 已成功
    FAILED = "failed"          # 失败
    EXPIRED = "expired"        # 已过期


class TransactionRecord(Base):
    """交易记录表 (transaction_records)

    记录所有资金流动,包括充值、消费和退款。
    """

    __tablename__ = "transaction_records"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 关联关系 ====================
    operator_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="运营商ID"
    )

    # ==================== 交易基础信息 ====================
    transaction_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="交易类型: recharge/consumption/refund"
    )

    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="交易金额(充值和退款为正,消费为负)"
    )

    # ==================== 余额快照(审计) ====================
    balance_before: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="交易前余额"
    )

    balance_after: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="交易后余额"
    )

    # ==================== 关联记录 ====================
    related_usage_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usage_records.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联使用记录ID(消费类型)"
    )

    related_refund_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,  # 先不设置FK,等refund_records表创建后再添加
        comment="关联退款记录ID(退款类型)"
    )

    # ==================== 支付信息(充值类型) ====================
    payment_channel: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="支付渠道: wechat/alipay(充值类型)"
    )

    payment_order_no: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="支付平台订单号"
    )

    payment_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="支付状态: pending/success/failed"
    )

    payment_callback_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="支付回调时间"
    )

    # ==================== 交易描述 ====================
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="交易描述"
    )

    # ==================== 审计字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment="创建时间"
    )

    # ==================== 关系定义 ====================
    # N:1 - 多条交易记录属于一个运营商
    operator: Mapped["OperatorAccount"] = relationship(
        "OperatorAccount",
        back_populates="transaction_records",
        lazy="selectin"
    )

    # N:1 - 多条交易记录关联一条使用记录(可选,仅消费类型)
    related_usage: Mapped[Optional["UsageRecord"]] = relationship(
        "UsageRecord",
        back_populates="transaction",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 交易类型枚举
        CheckConstraint(
            "transaction_type IN ('recharge', 'consumption', 'refund')",
            name="chk_trans_type"
        ),
        # CHECK约束: 支付渠道枚举(如果非空)
        CheckConstraint(
            "payment_channel IS NULL OR payment_channel IN ('wechat', 'alipay')",
            name="chk_payment_channel"
        ),
        # CHECK约束: 支付状态枚举(如果非空)
        CheckConstraint(
            "payment_status IS NULL OR payment_status IN ('pending', 'success', 'failed')",
            name="chk_payment_status"
        ),
        # CHECK约束: 余额计算正确性
        # 充值/消费: balance_after = balance_before + amount (amount可正可负)
        # 退款: balance_after = balance_before - amount (amount为正值)
        CheckConstraint(
            """
            (transaction_type != 'refund' AND balance_after = balance_before + amount) OR
            (transaction_type = 'refund' AND balance_after = balance_before - amount)
            """,
            name="chk_balance_calc"
        ),
        # 复合索引: 查询运营商交易记录(按时间降序)
        Index("idx_trans_operator", "operator_id", "created_at"),
        # 复合索引: 按类型统计
        Index("idx_trans_type", "transaction_type", "created_at"),
        # 条件索引: 支付回调查询(仅索引非空记录)
        Index(
            "idx_trans_payment",
            "payment_order_no",
            postgresql_where=text("payment_order_no IS NOT NULL")
        ),
        # 普通索引: 时间范围查询
        Index("idx_trans_date", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<TransactionRecord(id={self.id}, "
            f"type={self.transaction_type}, "
            f"amount={self.amount})>"
        )


class RechargeOrder(Base):
    """充值订单表 (recharge_orders)

    记录充值订单信息,包括支付状态和订单过期时间。
    订单创建后通过支付回调更新状态,成功后创建TransactionRecord。
    """

    __tablename__ = "recharge_orders"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键UUID"
    )

    # ==================== 订单信息 ====================
    order_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        comment="订单ID(业务键): ord_recharge_<timestamp>_<uuid>"
    )

    operator_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="运营商ID"
    )

    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="充值金额(10-10000元)"
    )

    payment_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="支付方式: wechat/alipay"
    )

    # ==================== 支付信息 ====================
    qr_code_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="支付二维码URL"
    )

    payment_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="支付页面URL(H5场景)"
    )

    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="支付平台交易ID(回调后填充)"
    )

    # ==================== 订单状态 ====================
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="订单状态: pending(待支付)/success(已支付)/failed(支付失败)/expired(已过期)"
    )

    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="订单过期时间(创建后30分钟)"
    )

    paid_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="支付完成时间(回调后填充)"
    )

    # ==================== 错误信息(失败时) ====================
    error_code: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="错误码(status=failed时)"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="错误信息(status=failed时)"
    )

    # ==================== 审计字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment="创建时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间"
    )

    # ==================== 关系定义 ====================
    # NOTE: RechargeOrder表暂未创建,operator关系已注释
    # operator: Mapped["OperatorAccount"] = relationship(
    #     "OperatorAccount",
    #     back_populates="recharge_orders",
    #     lazy="selectin"
    # )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 金额范围10-10000元
        CheckConstraint(
            "amount >= 10.00 AND amount <= 10000.00",
            name="chk_recharge_amount_range"
        ),
        # CHECK约束: 支付方式枚举
        CheckConstraint(
            "payment_method IN ('wechat', 'alipay')",
            name="chk_payment_method"
        ),
        # CHECK约束: 订单状态枚举
        CheckConstraint(
            "status IN ('pending', 'success', 'failed', 'expired')",
            name="chk_order_status"
        ),
        # 唯一索引: order_id业务键
        Index("idx_order_id", "order_id", unique=True),
        # 复合索引: 查询运营商订单(按时间降序)
        Index("idx_recharge_operator", "operator_id", "created_at"),
        # 普通索引: 按状态查询
        Index("idx_recharge_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<RechargeOrder(id={self.id}, "
            f"order_id={self.order_id}, "
            f"amount={self.amount}, "
            f"status={self.status})>"
        )
