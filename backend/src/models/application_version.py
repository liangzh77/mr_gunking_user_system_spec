"""应用版本模型 (ApplicationVersion)

存储应用的所有历史版本信息，包括APK下载链接。
"""

from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    TIMESTAMP,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class ApplicationVersion(Base):
    """应用版本表 (application_versions)

    存储应用的所有历史版本信息。
    """

    __tablename__ = "application_versions"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 关联信息 ====================
    application_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属应用ID"
    )

    # ==================== 版本信息 ====================
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="版本号(如 1.0.3)"
    )

    filename: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="原始文件名"
    )

    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="七牛云存储路径(如 apk/应用名/文件名.apk)"
    )

    apk_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="APK下载链接"
    )

    file_size: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="文件大小(字节)"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="版本说明"
    )

    # ==================== 审计字段 ====================
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment="上传时间"
    )

    uploaded_by: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="上传者(管理员ID)"
    )

    # ==================== 关系定义 ====================
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="versions",
        lazy="selectin"
    )

    uploader: Mapped[Optional["AdminAccount"]] = relationship(
        "AdminAccount",
        lazy="selectin"
    )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # 索引: 按应用ID查询
        Index("idx_app_version_app_id", "application_id"),
        # 索引: 按版本号查询
        Index("idx_app_version_version", "version"),
        # 索引: 按创建时间排序
        Index("idx_app_version_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationVersion(id={self.id}, "
            f"version={self.version}, "
            f"filename={self.filename})>"
        )
