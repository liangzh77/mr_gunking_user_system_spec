"""使用记录相关的Pydantic Schemas (T042)

此模块定义使用记录(UsageRecord)的数据模型。
用于API响应和数据序列化。
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UsageRecordBase(BaseModel):
    """使用记录基础模型"""

    session_id: str = Field(
        ...,
        description="游戏会话ID(幂等性标识)",
        pattern=r'^[a-zA-Z0-9]+_\d+_[a-zA-Z0-9]{16}$',
        examples=["550e8400_1728540000_a1b2c3d4e5f6g7h8"]
    )

    player_count: int = Field(
        ...,
        description="玩家数量",
        ge=1,
        le=100,
        examples=[5]
    )

    price_per_player: str = Field(
        ...,
        description="单人价格快照(历史价格)",
        pattern=r'^\d+\.\d{2}$',
        examples=["10.00"]
    )

    total_cost: str = Field(
        ...,
        description="总费用",
        pattern=r'^\d+\.\d{2}$',
        examples=["50.00"]
    )


class UsageRecordCreate(UsageRecordBase):
    """创建使用记录的请求模型

    内部使用,不对外暴露
    """

    operator_id: UUID
    site_id: UUID
    application_id: UUID
    authorization_token: str
    client_ip: Optional[str] = None


class UsageRecordInDB(UsageRecordBase):
    """数据库中的使用记录完整模型"""

    id: UUID = Field(..., description="使用记录ID")
    operator_id: UUID = Field(..., description="运营商ID")
    site_id: UUID = Field(..., description="运营点ID")
    application_id: UUID = Field(..., description="应用ID")
    authorization_token: str = Field(..., description="授权令牌")
    game_started_at: datetime = Field(..., description="游戏启动时间")
    game_duration_minutes: Optional[int] = Field(None, description="游戏时长(分钟)")
    game_ended_at: Optional[datetime] = Field(None, description="游戏结束时间")
    client_ip: Optional[str] = Field(None, description="请求来源IP")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True  # Pydantic v2: 允许从ORM对象创建


class UsageRecordResponse(UsageRecordBase):
    """使用记录响应模型(对外API)"""

    id: UUID = Field(..., description="使用记录ID")
    app_name: str = Field(..., description="应用名称")
    site_name: str = Field(..., description="运营点名称")
    game_started_at: datetime = Field(..., description="游戏启动时间")
    game_duration_minutes: Optional[int] = Field(None, description="游戏时长(分钟)")
    game_ended_at: Optional[datetime] = Field(None, description="游戏结束时间")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "aa0e8400-e29b-41d4-a716-446655440005",
                "session_id": "550e8400_1728540000_a1b2c3d4e5f6g7h8",
                "app_name": "太空探险",
                "site_name": "北京朝阳门店",
                "player_count": 5,
                "price_per_player": "10.00",
                "total_cost": "50.00",
                "game_started_at": "2025-10-10T14:30:00+08:00",
                "game_duration_minutes": 45,
                "game_ended_at": "2025-10-10T15:15:00+08:00"
            }
        }
