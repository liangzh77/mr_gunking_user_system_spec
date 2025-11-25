"""应用授权申请模式关联模型

此模型表示运营商申请授权时请求的具体应用模式。
一个申请可以包含多个模式。
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
    from .app_request import ApplicationRequest
    from .application_mode import ApplicationMode


class ApplicationRequestMode(Base):
    """应用授权申请模式关联表 (application_request_modes)

    关联授权申请和具体的应用模式。
    """

    __tablename__ = "application_request_modes"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 关联字段 ====================
    request_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_requests.id", ondelete="CASCADE"),
        nullable=False,
        comment="申请ID"
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
    # N:1 - 多个关联属于一个申请
    request: Mapped["ApplicationRequest"] = relationship(
        "ApplicationRequest",
        back_populates="requested_modes"
    )

    # N:1 - 多个关联指向一个模式
    mode: Mapped["ApplicationMode"] = relationship(
        "ApplicationMode",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # UNIQUE约束: 同一申请下不能重复添加相同模式
        Index("uq_request_mode", "request_id", "application_mode_id", unique=True),
        # 普通索引: 按申请查询模式
        Index("idx_req_mode_req_id", "request_id"),
        # 普通索引: 按模式查询申请
        Index("idx_req_mode_mode_id", "application_mode_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationRequestMode(id={self.id}, "
            f"request_id={self.request_id}, "
            f"mode_id={self.application_mode_id})>"
        )
