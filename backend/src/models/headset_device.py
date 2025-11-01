"""头显设备模型 (HeadsetDevice)

此模型存储头显设备信息，用于追踪设备使用记录。

关键特性:
- 归属于运营点(N:1关系)
- 自动管理首次和最后使用时间
- 支持设备状态管理
"""

from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID, uuid4

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    TIMESTAMP,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class HeadsetDevice(Base):
    """头显设备表 (headset_devices)

    存储头显设备的基本信息和使用状态。
    """

    __tablename__ = "headset_devices"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 设备标识 ====================
    device_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="设备唯一ID"
    )

    # ==================== 归属关系 ====================
    site_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operation_sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="所属运营点ID"
    )

    # ==================== 设备信息 ====================
    device_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="设备名称"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="设备状态: active/inactive"
    )

    # ==================== 使用时间追踪 ====================
    first_used_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="首次使用时间"
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="最后使用时间"
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
    # N:1 - 多个设备属于一个运营点
    site: Mapped["OperationSite"] = relationship(
        "OperationSite",
        back_populates="headset_devices",
        lazy="selectin"
    )

    # 1:N - 一个设备有多条游戏记录
    game_records: Mapped[list["HeadsetGameRecord"]] = relationship(
        "HeadsetGameRecord",
        back_populates="headset_device",
        lazy="select"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        Index("idx_headset_devices_site", "site_id"),
        Index("idx_headset_devices_device_id", "device_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<HeadsetDevice(id={self.id}, "
            f"device_id={self.device_id}, "
            f"site_id={self.site_id})>"
        )
