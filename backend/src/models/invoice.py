"""发票记录模型 (InvoiceRecord) - T056

此模型对应数据模型中的 invoice_records 表。
记录运营商的发票申请、审核状态和PDF生成。

关键特性:
- 发票状态: pending/approved/rejected
- 审核流程: 财务人员审核
- PDF生成: 审核通过后生成PDF下载链接
- 发票信息: 发票抬头、税号、接收邮箱
- 审计完整性: 记录审核人、审核时间、拒绝原因

业务规则(契约):
- 开票金额不能超过已充值金额(由API层验证)
- email可选,默认使用账户邮箱
- pdf_url仅在status=approved时有值
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    DECIMAL,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class InvoiceRecord(Base):
    """发票记录表 (invoice_records)

    记录运营商的发票申请和审核流程。
    """

    __tablename__ = "invoice_records"

    # ==================== 主键 ====================
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 关联关系 ====================
    operator_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="运营商ID"
    )

    # ==================== 发票申请信息 ====================
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="开票金额(不能超过已充值金额)"
    )

    invoice_title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="发票抬头(公司名称)"
    )

    tax_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="纳税人识别号(15-20位字母数字)"
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="接收发票的邮箱(可选,默认使用账户邮箱)"
    )

    # ==================== 审核状态 ====================
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="审核状态: pending/approved/rejected"
    )

    pdf_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="发票PDF下载链接(status=approved时生成)"
    )

    reject_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="拒绝原因(status=rejected时必填)"
    )

    # ==================== 审核信息 ====================
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        # TODO: 添加ForeignKey当finance_accounts表创建后
        # ForeignKey("finance_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="审核人ID(财务人员,暂不设置FK)"
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
    # N:1 - 多条发票记录属于一个运营商
    operator: Mapped["OperatorAccount"] = relationship(
        "OperatorAccount",
        back_populates="invoice_records",
        lazy="selectin"
    )

    # TODO: 添加reviewer relationship当finance_accounts表创建后
    # reviewer: Mapped[Optional["FinanceAccount"]] = relationship(
    #     "FinanceAccount",
    #     foreign_keys=[reviewed_by],
    #     lazy="selectin"
    # )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 审核状态枚举
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="chk_invoice_status"
        ),
        # CHECK约束: 开票金额必须为正数
        CheckConstraint(
            "amount > 0",
            name="chk_invoice_amount_positive"
        ),
        # CHECK约束: 税号长度(格式验证由Pydantic schema层处理,避免SQLite兼容问题)
        CheckConstraint(
            "LENGTH(tax_id) >= 15 AND LENGTH(tax_id) <= 20",
            name="chk_invoice_tax_id_length"
        ),
        # CHECK约束: 审核通过/拒绝时必须有审核人和审核时间
        CheckConstraint(
            "(status = 'pending') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="chk_invoice_reviewed_required"
        ),
        # CHECK约束: 拒绝时必须有拒绝原因
        CheckConstraint(
            "(status != 'rejected') OR (reject_reason IS NOT NULL)",
            name="chk_invoice_reject_reason_required"
        ),
        # CHECK约束: 审核通过时必须有PDF链接
        CheckConstraint(
            "(status != 'approved') OR (pdf_url IS NOT NULL)",
            name="chk_invoice_pdf_url_required"
        ),
        # 复合索引: 查询运营商发票记录(按时间降序)
        Index("idx_invoice_operator", "operator_id", "created_at"),
        # 复合索引: 按状态查询(待审核列表)
        Index("idx_invoice_status", "status", "created_at"),
        # 索引: 审核人查询
        Index("idx_invoice_reviewer", "reviewed_by"),
        # 索引: 税号查询(防止重复开票)
        Index("idx_invoice_tax_id", "operator_id", "tax_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<InvoiceRecord(id={self.id}, "
            f"operator_id={self.operator_id}, "
            f"amount={self.amount}, "
            f"status={self.status})>"
        )
