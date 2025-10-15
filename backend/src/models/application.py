"""应用模型 (Application)

此模型对应 data-model.md 中的 applications 表。
应用是可授权的MR游戏,定义游戏的基础信息和定价规则。

关键特性:
- 唯一的app_code标识符
- 定价规则(单人价格 + 玩家数范围)
- 上架/下架状态管理
- 创建者追踪(管理员)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

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


class Application(Base):
    """应用表 (applications)

    存储可授权的MR游戏应用信息,包括定价和玩家数限制。
    """

    __tablename__ = "applications"

    # ==================== 主键 ====================
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 应用信息 ====================
    app_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment="应用唯一标识符(用于API调用)"
    )

    app_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="应用名称"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="应用描述"
    )

    # ==================== 定价规则 ====================
    price_per_player: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="单人价格(单位:元)"
    )

    min_players: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="最小玩家数"
    )

    max_players: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="最大玩家数"
    )

    # ==================== 状态管理 ====================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="应用状态(下架后不可新授权)"
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

    created_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建者(管理员ID)"
    )

    # ==================== 关系定义 ====================
    # N:1 - 多个应用由一个管理员创建
    creator: Mapped[Optional["AdminAccount"]] = relationship(
        "AdminAccount",
        back_populates="created_applications",
        lazy="selectin"
    )

    # 1:N - 一个应用可授权给多个运营商
    authorizations: Mapped[list["OperatorAppAuthorization"]] = relationship(
        "OperatorAppAuthorization",
        back_populates="application",
        lazy="selectin"
    )

    # 1:N - 一个应用产生多条使用记录
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord",
        back_populates="application",
        lazy="selectin"
    )

    # 1:N - 一个应用有多个授权申请
    requests: Mapped[list["ApplicationRequest"]] = relationship(
        "ApplicationRequest",
        back_populates="application",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 价格必须为正数
        CheckConstraint(
            "price_per_player > 0",
            name="chk_price_positive"
        ),
        # CHECK约束: 玩家数范围合理性
        # - 最小玩家数 >= 1
        # - 最大玩家数 >= 最小玩家数
        # - 最大玩家数 <= 100
        CheckConstraint(
            "min_players >= 1 AND max_players >= min_players AND max_players <= 100",
            name="chk_players_range"
        ),
        # UNIQUE索引: app_code全局唯一
        Index("uq_app_code", "app_code", unique=True),
        # 普通索引: 名称搜索
        Index("idx_app_name", "app_name"),
        # 普通索引: 查询活跃应用
        Index("idx_app_active", "is_active"),
        # 普通索引: 价格统计
        Index("idx_app_price", "price_per_player"),
    )

    def __repr__(self) -> str:
        return (
            f"<Application(id={self.id}, "
            f"code={self.app_code}, "
            f"name={self.app_name}, "
            f"price={self.price_per_player})>"
        )
