"""运营商消息通知相关的Pydantic schemas"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, UUID4


# ========== 消息响应模型 ==========

class MessageItem(BaseModel):
    """消息列表项"""
    message_id: str = Field(..., description="消息ID")
    message_type: str = Field(..., description="消息类型: refund_approved, refund_rejected, invoice_approved, invoice_rejected, system_announcement")
    title: str = Field(..., description="消息标题")
    content: str = Field(..., description="消息内容")
    related_type: Optional[str] = Field(None, description="关联资源类型: refund, invoice")
    related_id: Optional[str] = Field(None, description="关联资源ID")
    is_read: bool = Field(..., description="是否已读")
    read_at: Optional[datetime] = Field(None, description="阅读时间")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """消息列表响应"""
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total: int = Field(..., description="总记录数")
    items: List[MessageItem] = Field(..., description="消息列表")


class UnreadCountResponse(BaseModel):
    """未读消息数量响应"""
    unread_count: int = Field(..., description="未读消息数量")


class MessageMarkReadResponse(BaseModel):
    """标记消息为已读响应"""
    message_id: str = Field(..., description="消息ID")
    read_at: datetime = Field(..., description="阅读时间")


class MessageMarkAllReadResponse(BaseModel):
    """标记所有消息为已读响应"""
    marked_count: int = Field(..., description="标记的消息数量")


class MessageDeleteResponse(BaseModel):
    """删除消息响应"""
    message: str = Field(default="消息已删除", description="响应消息")


# ========== 消息请求模型 ==========

class MessageQueryParams(BaseModel):
    """消息查询参数"""
    is_read: Optional[bool] = Field(None, description="是否已读筛选(None=全部)")
    message_type: Optional[str] = Field(None, description="消息类型筛选(None=全部)")
    page: int = Field(default=1, ge=1, description="页码(从1开始)")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ========== 消息发送相关(内部使用) ==========

class MessageCreate(BaseModel):
    """创建消息(内部使用)"""
    operator_id: UUID4 = Field(..., description="运营商ID")
    message_type: str = Field(..., description="消息类型")
    title: str = Field(..., max_length=200, description="消息标题")
    content: str = Field(..., description="消息内容")
    related_type: Optional[str] = Field(None, max_length=50, description="关联资源类型")
    related_id: Optional[UUID4] = Field(None, description="关联资源ID")
