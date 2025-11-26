"""运营商应用授权模式关联模型

此模型表示运营商被授权使用应用的哪些具体模式。
一个授权可以包含多个模式。
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import (
    ForeignKey,
    Index,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base

if TYPE_CHECKING:
    from .operator_app_authorization import OperatorAppAuthorization
    from .application_mode import ApplicationMode


class OperatorAppAuthorizationMode(Base):
    """运营商应用授权模式关联表 (operator_app_authorization_modes)

    关联授权和具体的应用模式。
    """

    __tablename__ = "operator_app_authorization_modes"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 关联字段 ====================
    authorization_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_app_authorizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="授权ID"
    )

    application_mode_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_modes.id", ondelete="CASCADE"),
        nullable=False,
        comment="应用模式ID"
    )

    # ==================== 审计字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment="创建时间"
    )

    # ==================== 关系定义 ====================
    # N:1 - 多个关联属于一个授权
    authorization: Mapped["OperatorAppAuthorization"] = relationship(
        "OperatorAppAuthorization",
        back_populates="authorized_modes"
    )

    # N:1 - 多个关联指向一个模式
    mode: Mapped["ApplicationMode"] = relationship(
        "ApplicationMode",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # UNIQUE约束: 同一授权下不能重复添加相同模式
        Index("uq_auth_mode", "authorization_id", "application_mode_id", unique=True),
        # 普通索引: 按授权查询模式
        Index("idx_auth_mode_auth_id", "authorization_id"),
        # 普通索引: 按模式查询授权
        Index("idx_auth_mode_mode_id", "application_mode_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<OperatorAppAuthorizationMode(id={self.id}, "
            f"auth_id={self.authorization_id}, "
            f"mode_id={self.application_mode_id})>"
        )
