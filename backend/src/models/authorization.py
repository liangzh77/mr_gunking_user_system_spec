"""运营者应用授权模型 (OperatorAppAuthorization)

此模型对应 data-model.md 中的 operator_app_authorizations 表。
管理运营商对应用的授权关系,控制运营商可使用的应用范围。

关键特性:
- 多对多关系映射(operator <-> application)
- 授权到期时间管理
- 授权审批流程追踪
- 唯一约束(operator + application + active)
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class OperatorAppAuthorization(Base):
    """运营者应用授权表 (operator_app_authorizations)

    管理运营商对应用的授权关系,控制授权有效期和状态。
    """

    __tablename__ = "operator_app_authorizations"

    # ==================== 主键 ====================
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 授权关系 ====================
    operator_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_accounts.id", ondelete="CASCADE"),
        nullable=False,
        comment="运营商ID"
    )

    application_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
        comment="应用ID"
    )

    # ==================== 授权时间管理 ====================
    authorized_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment="授权时间"
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="授权到期时间(NULL表示永久授权)"
    )

    # ==================== 审批信息 ====================
    authorized_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="授权审批人(管理员ID)"
    )

    application_request_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,  # 先不设置FK,等application_requests表创建后再添加
        comment="关联的申请记录ID(如通过申请授权)"
    )

    # ==================== 状态管理 ====================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="授权状态"
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
    # N:1 - 多个授权属于一个运营商
    operator: Mapped["OperatorAccount"] = relationship(
        "OperatorAccount",
        back_populates="app_authorizations",
        lazy="selectin"
    )

    # N:1 - 多个授权指向一个应用
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="authorizations",
        lazy="selectin"
    )

    # N:1 - 多个授权由一个管理员批准
    approver: Mapped[Optional["AdminAccount"]] = relationship(
        "AdminAccount",
        back_populates="approved_authorizations",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 到期时间必须晚于授权时间
        CheckConstraint(
            "expires_at IS NULL OR expires_at > authorized_at",
            name="chk_expiry_future"
        ),
        # UNIQUE索引: 同一运营商对同一应用只能有一条活跃授权
        Index(
            "uq_operator_app",
            "operator_id",
            "application_id",
            unique=True,
            postgresql_where=(Text("is_active = true"))
        ),
        # 复合索引: 查询运营商授权列表
        Index("idx_auth_operator", "operator_id", "is_active"),
        # 复合索引: 统计应用授权数量
        Index("idx_auth_application", "application_id", "is_active"),
        # 条件索引: 授权到期提醒(仅索引非空记录)
        Index(
            "idx_auth_expiry",
            "expires_at",
            postgresql_where=(Text("expires_at IS NOT NULL"))
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<OperatorAppAuthorization(id={self.id}, "
            f"operator_id={self.operator_id}, "
            f"app_id={self.application_id}, "
            f"active={self.is_active})>"
        )
