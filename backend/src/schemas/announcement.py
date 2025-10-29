"""系统公告Schema定义 (T212)

此模块定义系统公告相关的数据模型。
管理员可以发布系统公告，所有运营商都会收到。
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ========== 创建公告请求 ==========

class CreateAnnouncementRequest(BaseModel):
    """创建系统公告请求

    管理员发布系统公告给所有运营商。
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="公告标题",
        examples=["春节假期运营时间调整"]
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="公告内容",
        examples=["尊敬的运营商：春节期间（2月10日-2月17日）系统正常运营..."]
    )
    importance: str = Field(
        "normal",
        pattern="^(low|normal|high|urgent)$",
        description="重要程度: low(普通)/normal(一般)/high(重要)/urgent(紧急)",
        examples=["normal"]
    )

    class Config:
        from_attributes = True


# ========== 公告响应 ==========

class AnnouncementResponse(BaseModel):
    """系统公告响应

    返回公告的详细信息。
    """

    announcement_id: str = Field(
        ...,
        description="公告ID",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    title: str = Field(
        ...,
        description="公告标题"
    )
    content: str = Field(
        ...,
        description="公告内容"
    )
    importance: str = Field(
        ...,
        description="重要程度"
    )
    created_by: str = Field(
        ...,
        description="发布人ID（管理员）"
    )
    created_at: datetime = Field(
        ...,
        description="发布时间"
    )
    recipients_count: int = Field(
        ...,
        description="接收人数（运营商数量）",
        ge=0
    )

    class Config:
        from_attributes = True


# ========== 批量通知请求 ==========

class BulkNotificationRequest(BaseModel):
    """批量通知请求

    用于向多个运营商发送通知。
    """

    operator_ids: Optional[list[UUID]] = Field(
        None,
        description="运营商ID列表（不指定=发送给所有运营商）"
    )
    message_type: str = Field(
        ...,
        description="消息类型",
        examples=["system_announcement", "price_change", "balance_low"]
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="通知标题"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="通知内容"
    )
    related_type: Optional[str] = Field(
        None,
        description="关联资源类型",
        examples=["application", "announcement"]
    )
    related_id: Optional[UUID] = Field(
        None,
        description="关联资源ID"
    )

    class Config:
        from_attributes = True


# ========== 批量通知响应 ==========

class BulkNotificationResponse(BaseModel):
    """批量通知响应

    返回批量发送的结果。
    """

    success_count: int = Field(
        ...,
        description="成功发送数量",
        ge=0
    )
    failed_count: int = Field(
        ...,
        description="失败数量",
        ge=0
    )
    total_count: int = Field(
        ...,
        description="总数量",
        ge=0
    )

    class Config:
        from_attributes = True
