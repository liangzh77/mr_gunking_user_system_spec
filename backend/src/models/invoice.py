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
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    DECIMAL,
    TIMESTAMP,
)
from ..db.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class InvoiceRecord(Base):
    """发票记录表 (invoice_records)

    记录运营商的发票申请和审核流程。
    """

    __tablename__ = "invoice_records"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 关联关系 ====================
    operator_id: Mapped[PyUUID] = mapped_column(
        GUID,
        ForeignKey("operator_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="运营商ID"
    )

    # ==================== 发票申请信息 ====================
    invoice_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="发票类型: vat_normal/vat_special"
    )

    invoice_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="开票金额(不能超过已充值金额)"
    )

    invoice_title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="发票抬头(公司名称)"
    )

    tax_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="纳税人识别号"
    )

    bank_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="开户银行"
    )

    bank_account: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="银行账号"
    )

    company_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="公司地址"
    )

    company_phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="公司电话"
    )

    # ==================== 审核状态 ====================
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="审核状态: pending/approved/rejected/issued"
    )

    reject_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="拒绝原因(status=rejected时必填)"
    )

    invoice_number: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="发票号码"
    )

    invoice_file_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="发票PDF下载链接"
    )

    issued_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="开票时间"
    )

    # ==================== 审核信息 ====================
    reviewed_by: Mapped[Optional[PyUUID]] = mapped_column(
        GUID,
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
    requested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment="申请时间"
    )

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
    # N:1 - 多条发票记录属于一个运营商
    operator: Mapped["OperatorAccount"] = relationship(
        "OperatorAccount",
        back_populates="invoice_records",
        lazy="selectin"
    )

    # N:1 - 多条发票记录由一个财务人员审核
    reviewer: Mapped[Optional["FinanceAccount"]] = relationship(
        "FinanceAccount",
        foreign_keys=[reviewed_by],
        back_populates="reviewed_invoices",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 审核状态枚举
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'issued')",
            name="chk_invoice_status"
        ),
        # CHECK约束: 发票类型枚举
        CheckConstraint(
            "invoice_type IN ('vat_normal', 'vat_special')",
            name="chk_invoice_type"
        ),
        # CHECK约束: 开票金额必须为正数
        CheckConstraint(
            "invoice_amount > 0",
            name="chk_invoice_amount_positive"
        ),
        # 复合索引: 查询运营商发票记录(按时间降序)
        Index("idx_invoice_operator", "operator_id", "requested_at"),
        # 复合索引: 按状态查询(待审核列表)
        Index("idx_invoice_status", "status", "requested_at"),
        # 索引: 发票号码查询
        Index("idx_invoice_number", "invoice_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<InvoiceRecord(id={self.id}, "
            f"operator_id={self.operator_id}, "
            f"amount={self.invoice_amount}, "
            f"status={self.status})>"
        )
