"""银行转账充值申请模型 (BankTransferApplication)

此模型记录运营商的银行转账充值申请、凭证上传和审核流程。

关键特性:
- 申请状态: pending/approved/rejected
- 审核流程: 财务人员审核
- 凭证上传: 上传转账凭证图片URL
- 金额追踪: 申请充值金额
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


class BankTransferApplication(Base):
    """银行转账充值申请表 (bank_transfer_applications)

    记录运营商的银行转账充值申请和审核流程。
    """

    __tablename__ = "bank_transfer_applications"

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

    # ==================== 申请信息 ====================
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="申请充值金额"
    )

    voucher_image_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="转账凭证图片URL"
    )

    remark: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="申请备注(可选,最多500字符)"
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
    # N:1 - 多条申请记录属于一个运营商
    operator: Mapped["OperatorAccount"] = relationship(
        "OperatorAccount",
        back_populates="bank_transfer_applications",
        lazy="selectin"
    )

    # N:1 - 多条申请记录由一个财务人员审核
    reviewer: Mapped[Optional["FinanceAccount"]] = relationship(
        "FinanceAccount",
        foreign_keys=[reviewed_by],
        back_populates="reviewed_bank_transfers",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 审核状态枚举
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="chk_bank_transfer_status"
        ),
        # CHECK约束: 申请金额必须为正数
        CheckConstraint(
            "amount > 0",
            name="chk_bank_transfer_amount_positive"
        ),
        # CHECK约束: 审核通过/拒绝时必须有审核人和审核时间
        CheckConstraint(
            "(status = 'pending') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="chk_bank_transfer_reviewed_required"
        ),
        # CHECK约束: 拒绝时必须有拒绝原因
        CheckConstraint(
            "(status != 'rejected') OR (reject_reason IS NOT NULL)",
            name="chk_bank_transfer_reject_reason_required"
        ),
        # 复合索引: 查询运营商转账申请记录(按时间降序)
        Index("idx_bank_transfer_operator", "operator_id", "created_at"),
        # 复合索引: 按状态查询(待审核列表)
        Index("idx_bank_transfer_status", "status", "created_at"),
        # 索引: 审核人查询
        Index("idx_bank_transfer_reviewer", "reviewed_by"),
    )

    def __repr__(self) -> str:
        return (
            f"<BankTransferApplication(id={self.id}, "
            f"operator_id={self.operator_id}, "
            f"amount={self.amount}, "
            f"status={self.status})>"
        )
