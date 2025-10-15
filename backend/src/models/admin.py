"""Admin account ORM model."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class AdminAccount(Base):
    """Admin account model for system administrators.

    Attributes:
        id: Unique identifier (UUID)
        username: Unique username for login
        full_name: Full name of the administrator
        email: Contact email address
        phone: Contact phone number
        password_hash: Bcrypt hashed password
        role: Admin role (super_admin, admin, auditor)
        permissions: JSON array of permission strings
        is_active: Account active status
        last_login_at: Last login timestamp
        last_login_ip: Last login IP address
        created_by: Creator admin account ID (self-referential)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "admin_accounts"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
    )

    # Authentication fields
    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile fields
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)

    # Authorization fields
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="admin", index=True
    )
    permissions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    # Status fields
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Login tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Audit fields
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    # ==================== 关系定义 ====================
    # 1:N - 一个管理员创建多个应用
    created_applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="creator",
        lazy="selectin",
        foreign_keys="Application.created_by"
    )

    # 1:N - 一个管理员创建多个运营商账户
    created_operators: Mapped[list["OperatorAccount"]] = relationship(
        "OperatorAccount",
        back_populates="creator",
        lazy="selectin",
        foreign_keys="OperatorAccount.created_by"
    )

    # 1:N - 一个管理员批准多个授权关系
    approved_authorizations: Mapped[list["OperatorAppAuthorization"]] = relationship(
        "OperatorAppAuthorization",
        back_populates="approver",
        lazy="selectin",
        foreign_keys="OperatorAppAuthorization.authorized_by"
    )

    # 1:N - 一个管理员审核多个授权申请
    reviewed_requests: Mapped[list["ApplicationRequest"]] = relationship(
        "ApplicationRequest",
        back_populates="reviewer",
        lazy="selectin",
        foreign_keys="ApplicationRequest.reviewed_by"
    )

    def __repr__(self) -> str:
        """String representation of admin account."""
        return f"<AdminAccount(id={self.id}, username='{self.username}', role='{self.role}')>"

    def has_permission(self, permission: str) -> bool:
        """Check if admin has a specific permission.

        Args:
            permission: Permission string to check

        Returns:
            bool: True if admin has the permission
        """
        if self.role == "super_admin":
            return True

        if not isinstance(self.permissions, list):
            return False

        # Check for exact match or wildcard
        return permission in self.permissions or "*" in self.permissions

    def to_dict(self) -> dict:
        """Convert model to dictionary (excluding sensitive fields).

        Returns:
            dict: Model data without password_hash
        """
        return {
            "id": str(self.id),
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "last_login_ip": self.last_login_ip,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
