"""头显设备游戏记录模型 (HeadsetGameRecord)

此模型存储每个头显设备在一局游戏中的详细信息。

关键特性:
- 关联到游戏局(N:1关系)
- 关联到头显设备(N:1关系)
- 存储设备级别的时间和过程信息
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


class HeadsetGameRecord(Base):
    """头显设备游戏记录表 (headset_game_records)

    存储每个设备在一局游戏中的详细记录。
    """

    __tablename__ = "headset_game_records"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 关联关系 ====================
    game_session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的游戏局ID"
    )

    headset_device_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("headset_devices.id", ondelete="RESTRICT"),
        nullable=False,
        comment="关联的头显设备ID"
    )

    # ==================== 设备游戏时间 ====================
    start_time: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="设备开始时间"
    )

    end_time: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="设备结束时间"
    )

    # ==================== 过程信息 ====================
    process_info: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="设备过程信息"
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
    # N:1 - 多个设备记录属于一个游戏局
    game_session: Mapped["GameSession"] = relationship(
        "GameSession",
        back_populates="headset_records",
        lazy="selectin"
    )

    # N:1 - 多个记录关联到一个设备
    headset_device: Mapped["HeadsetDevice"] = relationship(
        "HeadsetDevice",
        back_populates="game_records",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        Index("idx_headset_game_records_session", "game_session_id"),
        Index("idx_headset_game_records_device", "headset_device_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<HeadsetGameRecord(id={self.id}, "
            f"game_session_id={self.game_session_id}, "
            f"headset_device_id={self.headset_device_id})>"
        )
