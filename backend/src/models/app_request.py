"""应用授权申请模型 (ApplicationRequest)

此模型用于管理运营商申请应用授权的流程。
运营商申请授权 → 管理员审批 → 通过后创建授权关系

关键特性:
- 申请状态管理(pending/approved/rejected)
- 审批流程追踪
- 拒绝原因记录
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class ApplicationRequest(Base):
    """应用授权申请表 (application_requests)

    运营商申请应用授权的记录,需要管理员审批。
    """

    __tablename__ = "application_requests"

    # ==================== 主键 ====================
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 申请信息 ====================
    operator_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_accounts.id", ondelete="CASCADE"),
        nullable=False,
        comment="申请运营商ID"
    )

    application_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
        comment="申请的应用ID"
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="申请理由"
    )

    # ==================== 审批信息 ====================
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="审核状态: pending/approved/rejected"
    )

    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="审核人(管理员ID)"
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="审核时间"
    )

    reject_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="拒绝原因(status=rejected时)"
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
    # N:1 - 多个申请属于一个运营商
    operator: Mapped["OperatorAccount"] = relationship(
        "OperatorAccount",
        back_populates="app_requests",
        lazy="selectin"
    )

    # N:1 - 多个申请指向一个应用
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="requests",
        lazy="selectin"
    )

    # N:1 - 多个申请由一个管理员审核
    reviewer: Mapped[Optional["AdminAccount"]] = relationship(
        "AdminAccount",
        back_populates="reviewed_requests",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 状态枚举
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="chk_request_status"
        ),
        # CHECK约束: 拒绝时必须有拒绝原因
        CheckConstraint(
            "(status = 'rejected' AND reject_reason IS NOT NULL) OR status != 'rejected'",
            name="chk_reject_reason_required"
        ),
        # CHECK约束: 审核通过/拒绝时必须有审核人和审核时间
        CheckConstraint(
            "(status IN ('approved', 'rejected') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL) OR status = 'pending'",
            name="chk_review_info_required"
        ),
        # UNIQUE索引: 同一运营商对同一应用只能有一条待审核的申请
        Index(
            "uq_operator_app_pending",
            "operator_id",
            "application_id",
            unique=True,
            postgresql_where=(Text("status = 'pending'"))
        ),
        # 复合索引: 查询运营商的申请列表
        Index("idx_request_operator", "operator_id", "created_at"),
        # 复合索引: 管理员查看待审核申请
        Index("idx_request_status", "status", "created_at"),
        # 普通索引: 按应用查询申请
        Index("idx_request_application", "application_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationRequest(id={self.id}, "
            f"operator_id={self.operator_id}, "
            f"app_id={self.application_id}, "
            f"status={self.status})>"
        )
