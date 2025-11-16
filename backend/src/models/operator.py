"""运营商账户模型 (OperatorAccount)

此模型对应 data-model.md 中的 operator_accounts 表。
运营商是系统的核心付费客户,负责运营MR游戏业务。

关键特性:
- 支持软删除 (deleted_at)
- 客户分级 (trial/standard/vip)
- 账户锁定机制 (is_locked)
- API Key认证
- 余额管理
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID as PyUUID, uuid4

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    DECIMAL,
    TIMESTAMP,
    text,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base


class OperatorAccount(Base):
    """运营商账户表 (operator_accounts)

    运营商是系统的核心客户,通过API Key认证访问游戏授权服务。
    """

    __tablename__ = "operator_accounts"

    # ==================== 主键 ====================
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="主键"
    )

    # ==================== 身份信息 ====================
    username: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="登录用户名,全局唯一"
    )

    full_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="真实姓名或公司名称"
    )

    phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="联系电话"
    )

    email: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="邮箱地址"
    )

    # ==================== 认证信息 ====================
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希(bcrypt)"
    )

    api_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="头显Server身份认证密钥"
    )

    api_key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="API Key哈希值(用于验证)"
    )

    # ==================== 账户状态 ====================
    balance: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="账户余额(单位:元)"
    )

    customer_tier: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="trial",
        comment="客户分类: vip/standard/trial"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="账户状态: true=正常, false=已注销"
    )

    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="账户锁定状态(用于异常检测)"
    )

    locked_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="锁定原因说明"
    )

    locked_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="锁定时间"
    )

    # ==================== 登录追踪 ====================
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="最近登录时间"
    )

    last_login_ip: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="最近登录IP"
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
    # Force reload trigger
    # NOTE: created_by字段在数据库schema中不存在,已注释
    # created_by: Mapped[Optional[PyUUID]] = mapped_column(
    #     UUID(as_uuid=True),
    #     ForeignKey("admin_accounts.id", ondelete="SET NULL"),
    #     nullable=True,
    #     comment="创建者(管理员ID)"
    # )

    # ==================== 关系定义 ====================
    # NOTE: creator关系已注释,因为created_by字段不存在
    # # N:1 - 多个运营商由一个管理员创建
    # creator: Mapped[Optional["AdminAccount"]] = relationship(
    #     "AdminAccount",
    #     back_populates="created_operators",
    #     lazy="selectin",
    #     foreign_keys=[created_by]
    # )
    # 1:N - 一个运营商拥有多个运营点
    operation_sites: Mapped[list["OperationSite"]] = relationship(
        "OperationSite",
        back_populates="operator",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # 1:N - 一个运营商有多个应用授权
    app_authorizations: Mapped[list["OperatorAppAuthorization"]] = relationship(
        "OperatorAppAuthorization",
        back_populates="operator",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # 1:N - 一个运营商产生多条使用记录
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord",
        back_populates="operator",
        lazy="selectin"
    )

    # 1:N - 一个运营商有多条交易记录
    transaction_records: Mapped[list["TransactionRecord"]] = relationship(
        "TransactionRecord",
        back_populates="operator",
        lazy="selectin"
    )

    # 1:N - 一个运营商有多条退款记录
    refund_records: Mapped[list["RefundRecord"]] = relationship(
        "RefundRecord",
        back_populates="operator",
        lazy="selectin"
    )

    # 1:N - 一个运营商有多条发票记录
    invoice_records: Mapped[list["InvoiceRecord"]] = relationship(
        "InvoiceRecord",
        back_populates="operator",
        lazy="selectin"
    )

    # 1:N - 一个运营商有多条银行转账充值申请
    bank_transfer_applications: Mapped[list["BankTransferApplication"]] = relationship(
        "BankTransferApplication",
        back_populates="operator",
        lazy="selectin"
    )

    # 1:N - 一个运营商有多条消息通知
    messages: Mapped[list["OperatorMessage"]] = relationship(
        "OperatorMessage",
        back_populates="operator",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # 1:N - 一个运营商有多个充值订单
    # NOTE: RechargeOrder表暂未创建,关系已注释
    # recharge_orders: Mapped[list["RechargeOrder"]] = relationship(
    #     "RechargeOrder",
    #     back_populates="operator",
    #     lazy="selectin"
    # )

    # 1:N - 一个运营商有多个应用授权申请
    # NOTE: ApplicationRequest表暂未创建,关系已注释
    # app_requests: Mapped[list["ApplicationRequest"]] = relationship(
    #     "ApplicationRequest",
    #     back_populates="operator",
    #     lazy="selectin"
    # )

    # ==================== 表级约束 ====================
    __table_args__ = (
        # CHECK约束: 余额非负
        CheckConstraint(
            "balance >= 0",
            name="chk_balance_non_negative"
        ),
        # CHECK约束: 客户分类枚举
        CheckConstraint(
            "customer_tier IN ('vip', 'standard', 'trial')",
            name="chk_customer_tier"
        ),
        # UNIQUE索引: username唯一(排除软删除记录)
        Index(
            "uq_operator_username",
            "username",
            unique=True,
            postgresql_where=text("deleted_at IS NULL")
        ),
        # UNIQUE索引: api_key唯一(排除软删除记录)
        Index(
            "uq_operator_api_key",
            "api_key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL")
        ),
        # 普通索引: 邮箱查询
        Index("idx_operator_email", "email"),
        # 复合索引: 客户分类统计
        Index("idx_operator_tier", "customer_tier", "is_active"),
        # 条件索引: 余额不足提醒(仅索引余额<100的记录)
        Index(
            "idx_operator_balance",
            "balance",
            postgresql_where=text("balance < 100")
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<OperatorAccount(id={self.id}, "
            f"username={self.username}, "
            f"tier={self.customer_tier}, "
            f"balance={self.balance})>"
        )
