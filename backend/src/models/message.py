"""运营商消息通知模型

此模型用于存储系统发送给运营商的消息通知
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from ..db.base import Base


class OperatorMessage(Base):
    """运营商消息通知表

    用于存储系统发送给运营商的各种通知消息，包括：
    - 退款审核结果通知
    - 发票审核结果通知
    - 系统公告
    - 其他业务通知
    """

    __tablename__ = "operator_messages"

    # 主键
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="消息ID")

    # 外键关联
    operator_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("operator_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="运营商ID"
    )

    # 消息内容
    message_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="消息类型: refund_approved, refund_rejected, invoice_approved, invoice_rejected, system_announcement"
    )
    title = Column(String(200), nullable=False, comment="消息标题")
    content = Column(Text, nullable=False, comment="消息内容")

    # 关联资源 (可选)
    related_type = Column(
        String(50),
        nullable=True,
        comment="关联资源类型: refund, invoice, 等"
    )
    related_id = Column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="关联资源ID"
    )

    # 状态
    is_read = Column(Boolean, nullable=False, default=False, comment="是否已读")
    read_at = Column(DateTime(timezone=True), nullable=True, comment="阅读时间")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="创建时间"
    )

    # 关系
    operator = relationship("OperatorAccount", back_populates="messages")

    # 索引
    __table_args__ = (
        Index("idx_operator_messages_operator_created", "operator_id", "created_at"),
        Index("idx_operator_messages_operator_read", "operator_id", "is_read"),
        Index("idx_operator_messages_type", "message_type"),
        {"comment": "运营商消息通知表"}
    )

    def __repr__(self):
        return f"<OperatorMessage(id={self.id}, operator_id={self.operator_id}, type={self.message_type}, is_read={self.is_read})>"
