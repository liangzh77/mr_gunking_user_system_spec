"""使用记录模型 (UsageRecord)

此模型对应 data-model.md 中的 usage_records 表。
记录每次游戏会话的详细信息,用于统计分析和财务审计。

关键特性:
- 唯一session_id防重复扣费(幂等性)
- 价格快照机制(历史价格追溯)
- 多表外键关联(operator/site/application)
- 游戏会话生命周期管理
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    DECIMAL,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class UsageRecord(Base):
    """使用记录表 (usage_records)

    记录每次游戏会话的详细信息,包括计费和会话状态。
    """

    __tablename__ = "usage_records"

    # ==================== 主键 ====================
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 会话标识(幂等性) ====================
    session_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        comment="游戏会话ID(防重复扣费)"
    )

    # ==================== 关联关系 ====================
    operator_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="运营商ID"
    )

    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operation_sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="运营点ID"
    )

    application_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
        comment="应用ID"
    )

    # ==================== 计费信息(历史快照) ====================
    player_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="玩家数量"
    )

    price_per_player: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="单人价格快照(历史价格)"
    )

    total_cost: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="总费用 = player_count × price_per_player"
    )

    # ==================== 授权信息 ====================
    authorization_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="授权令牌(返回给头显Server)"
    )

    # ==================== 会话生命周期 ====================
    game_started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment="游戏启动时间"
    )

    game_duration_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="游戏时长(分钟,头显Server上报)"
    )

    game_ended_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="游戏结束时间(头显Server上报)"
    )

    # ==================== 请求追踪 ====================
    client_ip: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="请求来源IP"
    )

    # ==================== 审计字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment="创建时间"
    )

    # ==================== 关系定义 ====================
    # N:1 - 多条使用记录属于一个运营商
    operator: Mapped["OperatorAccount"] = relationship(
        "OperatorAccount",
        back_populates="usage_records",
        lazy="selectin"
    )

    # N:1 - 多条使用记录属于一个运营点
    site: Mapped["OperationSite"] = relationship(
        "OperationSite",
        back_populates="usage_records",
        lazy="selectin"
    )

    # N:1 - 多条使用记录属于一个应用
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="usage_records",
        lazy="selectin"
    )

    # 1:1 - 每条使用记录对应一条交易记录
    transaction: Mapped[Optional["TransactionRecord"]] = relationship(
        "TransactionRecord",
        back_populates="related_usage",
        lazy="selectin",
        uselist=False
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 玩家数必须为正数
        CheckConstraint(
            "player_count > 0",
            name="chk_player_count_positive"
        ),
        # CHECK约束: 费用计算正确性
        CheckConstraint(
            "total_cost = player_count * price_per_player",
            name="chk_total_cost"
        ),
        # CHECK约束: 游戏时长为正数(如果非空)
        CheckConstraint(
            "game_duration_minutes IS NULL OR game_duration_minutes > 0",
            name="chk_game_duration"
        ),
        # UNIQUE索引: session_id全局唯一(幂等性保证)
        Index("uq_session_id", "session_id", unique=True),
        # 复合索引: 查询运营商使用记录(按时间降序)
        Index("idx_usage_operator", "operator_id", "game_started_at"),
        # 复合索引: 按运营点统计
        Index("idx_usage_site", "site_id", "game_started_at"),
        # 复合索引: 按应用统计
        Index("idx_usage_application", "application_id", "game_started_at"),
        # 普通索引: 时间范围查询
        Index("idx_usage_date", "game_started_at"),
        # 普通索引: 消费统计
        Index("idx_usage_cost", "total_cost"),
    )

    def __repr__(self) -> str:
        return (
            f"<UsageRecord(id={self.id}, "
            f"session_id={self.session_id}, "
            f"cost={self.total_cost})>"
        )
