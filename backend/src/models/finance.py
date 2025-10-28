"""
Financial Account Models (T160)

财务账号模型
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.db.base import Base


class FinanceAccount(Base):
    """
    财务账号表

    用于财务人员的独立账号系统，与运营商账号分离
    """
    __tablename__ = "finance_accounts"

    # 主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 认证信息
    username = Column(String(64), nullable=False, unique=True, comment="登录用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希(bcrypt)")

    # 个人信息
    full_name = Column(String(128), nullable=False, comment="真实姓名")
    phone = Column(String(32), nullable=False, comment="联系电话")
    email = Column(String(128), nullable=False, comment="邮箱地址")

    # 权限和角色
    role = Column(
        String(32),
        nullable=False,
        default="specialist",
        comment="角色: specialist/manager/auditor"
    )
    permissions = Column(JSON, nullable=False, server_default='[]', comment="权限配置(JSON数组)")

    # 账号状态
    is_active = Column(Boolean, nullable=False, default=True, comment="账号状态")

    # 登录追踪
    last_login_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="最近登录时间"
    )
    last_login_ip = Column(String(64), nullable=True, comment="最近登录IP")

    # 审计字段
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建者(管理员ID)"
    )

    # 关系
    # 一个财务人员审核多个退款
    reviewed_refunds = relationship(
        "RefundRecord",
        foreign_keys="[RefundRecord.reviewed_by]",
        back_populates="reviewer",
        lazy="select"
    )

    # 一个财务人员审核多个发票
    reviewed_invoices = relationship(
        "InvoiceRecord",
        foreign_keys="[InvoiceRecord.reviewed_by]",
        back_populates="reviewer",
        lazy="select"
    )

    # 一个财务人员产生多条操作记录
    operation_logs = relationship(
        "FinanceOperationLog",
        back_populates="finance_account",
        lazy="select"
    )

    # 与创建者的关系
    creator = relationship(
        "AdminAccount",
        foreign_keys=[created_by],
        lazy="select"
    )

    def __repr__(self):
        return f"<FinanceAccount(id={self.id}, username='{self.username}', role='{self.role}')>"


class FinanceOperationLog(Base):
    """
    财务操作记录表

    记录财务人员的所有关键操作，满足审计合规要求

    注意: 本表使用分区表设计(按月分区),提升大数据量下的查询性能
    """
    __tablename__ = "finance_operation_logs"

    # 复合主键 (id, created_at) - 用于分区表
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(
        TIMESTAMP(timezone=True),
        primary_key=True,
        nullable=False,
        default=datetime.utcnow,
        comment="操作时间"
    )

    # 外键
    finance_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("finance_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="财务账号ID"
    )

    # 操作信息
    operation_type = Column(
        String(64),
        nullable=False,
        comment="操作类型: review_refund/review_invoice/export_report等"
    )
    target_resource_type = Column(
        String(64),
        nullable=True,
        comment="目标资源类型: refund/invoice/report"
    )
    target_resource_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="目标资源ID"
    )
    operation_details = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="操作详情(JSON对象)"
    )

    # 审计信息
    ip_address = Column(String(64), nullable=False, comment="操作来源IP")
    user_agent = Column(String, nullable=True, comment="浏览器User-Agent")

    # 关系
    finance_account = relationship(
        "FinanceAccount",
        back_populates="operation_logs",
        lazy="select"
    )

    def __repr__(self):
        return (
            f"<FinanceOperationLog("
            f"id={self.id}, "
            f"finance_account_id={self.finance_account_id}, "
            f"operation_type='{self.operation_type}', "
            f"created_at={self.created_at}"
            f")>"
        )

    # 注意: 分区表的创建需要在数据库迁移脚本中单独处理
    # 例如:
    # CREATE TABLE finance_operation_logs (...) PARTITION BY RANGE (created_at);
    # CREATE TABLE finance_operation_logs_2025_10 PARTITION OF finance_operation_logs
    #     FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
