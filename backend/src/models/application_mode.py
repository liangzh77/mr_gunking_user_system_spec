"""应用模式模型 (ApplicationMode)

应用模式定义了应用的不同游戏模式（如：5分钟、10分钟、15分钟等），
每个模式有独立的价格设置。

关键特性:
- 一个应用可以有多个模式
- 每个模式有独立的价格
- 支持启用/禁用状态
- 历史使用记录通过快照保护，不受模式修改/删除影响
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DECIMAL,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base

if TYPE_CHECKING:
    from .application import Application


class ApplicationMode(Base):
    """应用模式表 (application_modes)

    存储应用的不同游戏模式和价格配置。
    """

    __tablename__ = "application_modes"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 关联字段 ====================
    application_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属应用ID"
    )

    # ==================== 模式信息 ====================
    mode_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="模式名称（如：5分钟、10分钟、15分钟）"
    )

    price: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="模式价格(单位:元)"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="模式描述"
    )

    # ==================== 显示设置 ====================
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="排序顺序（数字越小越靠前）"
    )

    # ==================== 状态管理 ====================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用"
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
    # N:1 - 多个模式属于一个应用
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="modes",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 价格必须为正数
        CheckConstraint(
            "price > 0",
            name="chk_mode_price_positive"
        ),
        # UNIQUE约束: 同一应用下模式名称唯一
        Index("uq_app_mode_name", "application_id", "mode_name", unique=True),
        # 普通索引: 按应用查询模式
        Index("idx_app_mode_app_id", "application_id"),
        # 普通索引: 查询活跃模式
        Index("idx_app_mode_active", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationMode(id={self.id}, "
            f"app_id={self.application_id}, "
            f"name={self.mode_name}, "
            f"price={self.price})>"
        )
