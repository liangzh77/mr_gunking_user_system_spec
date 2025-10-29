"""玩家分布统计Schema定义 (T197)

此模块定义玩家数量分布统计的数据模型。
用于分析不同玩家数量（2人、3-4人、5-8人等）的游戏场次分布。
"""

from typing import List
from pydantic import BaseModel, Field


# ========== 玩家数量分布统计 (T202) ==========

class PlayerDistributionItem(BaseModel):
    """玩家数量分布项

    表示某个玩家数量（或玩家数量范围）的统计数据。
    """

    player_count: int = Field(
        ...,
        description="玩家数量",
        examples=[4],
        ge=1,
        le=100
    )
    session_count: int = Field(
        ...,
        description="该玩家数的游戏场次",
        examples=[250],
        ge=0
    )
    percentage: float = Field(
        ...,
        description="占比(%)",
        examples=[25.0],
        ge=0,
        le=100
    )
    total_revenue: str = Field(
        ...,
        description="该玩家数的总收入(格式化为两位小数)",
        pattern=r'^\d+\.\d{2}$',
        examples=["10000.00"]
    )

    class Config:
        from_attributes = True


class PlayerDistributionResponse(BaseModel):
    """玩家数量分布统计响应

    用于分析玩家数量偏好，展示：
    - 2人游戏占比
    - 3-4人游戏占比
    - 5-8人游戏占比
    等数据，可用于生成饼图或柱状图。
    """

    distribution: List[PlayerDistributionItem] = Field(
        ...,
        description="玩家数量分布列表"
    )
    total_sessions: int = Field(
        ...,
        description="总游戏场次",
        examples=[1000],
        ge=0
    )
    most_common_player_count: int = Field(
        ...,
        description="最常见的玩家数量",
        examples=[4],
        ge=1
    )

    class Config:
        from_attributes = True
