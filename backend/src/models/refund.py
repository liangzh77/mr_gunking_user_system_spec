"""退款记录模型 (RefundRecord)

此模型对应 data-model.md 中的 refund_records 表。
记录运营商的退款申请、审核状态和审核历史。

关键特性:
- 退款状态: pending/approved/rejected
- 审核流程: 财务人员审核
- 金额追踪: 申请金额和实际退款金额可能不同
- 审计完整性: 记录审核人、审核时间、拒绝原因
"""

from datetime import datetime
from decimal import Decimal
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
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class RefundRecord(Base):
    """退款记录表 (refund_records)

    记录运营商的退款申请和审核流程。
    """

    __tablename__ = "refund_records"

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

    # ==================== 退款申请信息 ====================
    requested_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="申请退款金额(申请时的账户余额)"
    )

    actual_amount: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2),
        nullable=True,
        comment="实际退款金额(审核时的账户余额,可能小于申请金额)"
    )

    refund_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="退款原因(10-500字符)"
    )

    # ==================== 审核状态 ====================
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="审核状态: pending/approved/rejected"
    )

    reject_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="拒绝原因(status=rejected时必填)"
    )

    # ==================== 审核信息 ====================
    reviewed_by: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("finance_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="审核人ID(财务人员)"
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="审核时间"
    )

    # ==================== 审计字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment="申请时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间"
    )

    # ==================== 关系定义 ====================
    # N:1 - 多条退款记录属于一个运营商
    operator: Mapped["OperatorAccount"] = relationship(
        "OperatorAccount",
        back_populates="refund_records",
        lazy="selectin"
    )

    # N:1 - 多条退款记录由一个财务人员审核
    reviewer: Mapped[Optional["FinanceAccount"]] = relationship(
        "FinanceAccount",
        foreign_keys=[reviewed_by],
        back_populates="reviewed_refunds",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 审核状态枚举
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="chk_refund_status"
        ),
        # CHECK约束: 申请金额必须为正数
        CheckConstraint(
            "requested_amount > 0",
            name="chk_refund_requested_positive"
        ),
        # CHECK约束: 实际退款金额必须为正数(如果非空)
        CheckConstraint(
            "actual_amount IS NULL OR actual_amount > 0",
            name="chk_refund_actual_positive"
        ),
        # CHECK约束: 实际退款金额不能超过申请金额
        CheckConstraint(
            "actual_amount IS NULL OR actual_amount <= requested_amount",
            name="chk_refund_actual_lte_requested"
        ),
        # CHECK约束: 审核通过/拒绝时必须有审核人和审核时间
        CheckConstraint(
            "(status = 'pending') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="chk_refund_reviewed_required"
        ),
        # CHECK约束: 拒绝时必须有拒绝原因
        CheckConstraint(
            "(status != 'rejected') OR (reject_reason IS NOT NULL)",
            name="chk_refund_reject_reason_required"
        ),
        # 复合索引: 查询运营商退款记录(按时间降序)
        Index("idx_refund_operator", "operator_id", "created_at"),
        # 复合索引: 按状态查询(待审核列表)
        Index("idx_refund_status", "status", "created_at"),
        # 索引: 审核人查询
        Index("idx_refund_reviewer", "reviewed_by"),
    )

    def __repr__(self) -> str:
        return (
            f"<RefundRecord(id={self.id}, "
            f"operator_id={self.operator_id}, "
            f"amount={self.requested_amount}, "
            f"status={self.status})>"
        )
