"""MR游戏SDK数据模型"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(description="请求是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    error_code: Optional[str] = Field(None, description="错误代码")


class AuthorizeResponse(BaseResponse):
    """游戏授权响应"""
    auth_token: Optional[str] = Field(None, description="授权令牌")
    session_id: Optional[str] = Field(None, description="会话ID")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    player_count: Optional[int] = Field(None, description="玩家数量")
    billing_rate: Optional[float] = Field(None, description="计费费率")
    estimated_cost: Optional[float] = Field(None, description="预估费用")


class EndSessionResponse(BaseResponse):
    """结束会话响应"""
    session_id: Optional[str] = Field(None, description="会话ID")
    final_player_count: Optional[int] = Field(None, description="最终玩家数量")
    total_duration: Optional[int] = Field(None, description="总时长(秒)")
    total_cost: Optional[float] = Field(None, description="总费用")
    transaction_id: Optional[str] = Field(None, description="交易ID")


class BalanceResponse(BaseResponse):
    """余额查询响应"""
    balance: Optional[float] = Field(None, description="当前余额")
    currency: Optional[str] = Field("CNY", description="货币单位")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class TransactionItem(BaseModel):
    """交易记录项"""
    transaction_id: str = Field(description="交易ID")
    transaction_type: str = Field(description="交易类型")
    amount: float = Field(description="金额")
    balance_before: float = Field(description="交易前余额")
    balance_after: float = Field(description="交易后余额")
    description: str = Field(description="描述")
    created_at: datetime = Field(description="创建时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class TransactionListResponse(BaseResponse):
    """交易记录列表响应"""
    items: List[TransactionItem] = Field(default_factory=list, description="交易记录列表")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")


class UsageRecordItem(BaseModel):
    """使用记录项"""
    record_id: str = Field(description="记录ID")
    app_id: int = Field(description="应用ID")
    session_id: str = Field(description="会话ID")
    player_count: int = Field(description="玩家数量")
    duration: int = Field(description="持续时间(秒)")
    cost: float = Field(description="费用")
    created_at: datetime = Field(description="创建时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class UsageRecordListResponse(BaseResponse):
    """使用记录列表响应"""
    items: List[UsageRecordItem] = Field(default_factory=list, description="使用记录列表")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")