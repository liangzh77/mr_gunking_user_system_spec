"""运营点模型 (OperationSite)

此模型对应 data-model.md 中的 operation_sites 表。
运营点是运营商的线下门店或业务单元,每个运营点关联一个头显Server。

关键特性:
- 归属于运营商(N:1关系)
- 支持软删除
- 头显Server标识符关联
- 运营点状态管理
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
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


class OperationSite(Base):
    """运营点表 (operation_sites)

    存储运营商的线下门店信息,每个运营点对应一个头显Server设备。
    """

    __tablename__ = "operation_sites"

    # ==================== 主键 ====================
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 归属关系 ====================
    operator_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="所属运营商ID"
    )

    # ==================== 运营点信息 ====================
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="运营点名称"
    )

    address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="详细地址"
    )

    contact_person: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="现场负责人"
    )

    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="现场联系电话"
    )

    # ==================== 设备关联 ====================
    server_identifier: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="头显Server设备标识符"
    )

    # ==================== 状态管理 ====================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="运营点状态"
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

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="删除时间(软删除)"
    )

    # ==================== 关系定义 ====================
    # N:1 - 多个运营点属于一个运营商
    operator: Mapped["OperatorAccount"] = relationship(
        "OperatorAccount",
        back_populates="operation_sites",
        lazy="selectin"
    )

    # 1:N - 一个运营点产生多条使用记录
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord",
        back_populates="site",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # 复合索引: 查询运营商的活跃运营点
        Index("idx_site_operator", "operator_id", "is_active"),
        # 普通索引: 名称搜索
        Index("idx_site_name", "name"),
        # 条件索引: Server关联查询(仅索引非空记录)
        Index(
            "idx_site_server",
            "server_identifier",
            postgresql_where=(Text("server_identifier IS NOT NULL"))
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<OperationSite(id={self.id}, "
            f"name={self.name}, "
            f"operator_id={self.operator_id})>"
        )
