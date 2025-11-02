"""游戏局模型 (GameSession)

此模型存储一局游戏的详细信息。

关键特性:
- 关联到游戏使用记录(N:1关系)
- 存储游戏时间和过程信息
- 支持多个头显设备的游戏记录
"""

from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID, uuid4

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    ForeignKey,
    Index,
    Text,
    TIMESTAMP,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class GameSession(Base):
    """游戏局信息表 (game_sessions)

    存储每一局游戏的详细信息。
    """

    __tablename__ = "game_sessions"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 关联关系 ====================
    usage_record_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usage_records.id", ondelete="RESTRICT"),
        nullable=False,
        comment="关联的使用记录ID"
    )

    # ==================== 游戏时间 ====================
    start_time: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="游戏开始时间"
    )

    end_time: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="游戏结束时间"
    )

    # ==================== 过程信息 ====================
    process_info: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="游戏过程信息"
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
    # N:1 - 多个游戏局对应一个使用记录
    usage_record: Mapped["UsageRecord"] = relationship(
        "UsageRecord",
        back_populates="game_sessions",
        lazy="selectin"
    )

    # 1:N - 一个游戏局有多个设备记录
    headset_records: Mapped[list["HeadsetGameRecord"]] = relationship(
        "HeadsetGameRecord",
        back_populates="game_session",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        Index("idx_game_sessions_usage", "usage_record_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<GameSession(id={self.id}, "
            f"usage_record_id={self.usage_record_id})>"
        )
