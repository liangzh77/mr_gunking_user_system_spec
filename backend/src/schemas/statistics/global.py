"""全局统计Schema定义 (T196)

此模块定义管理员使用的全局统计数据模型。
包括全局仪表盘和多维度交叉分析的数据结构。
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ========== 枚举类型 ==========

class DimensionType(str, Enum):
    """维度类型"""
    OPERATOR = "operator"
    SITE = "site"
    APPLICATION = "application"


# ========== 全局统计仪表盘 (T199) ==========

class GlobalDashboardResponse(BaseModel):
    """全局统计仪表盘响应

    用于管理员查看系统全局统计数据，包括：
    - 总运营商数量
    - 总游戏场次
    - 总玩家人次
    - 总收入

    支持时间筛选。
    """

    total_operators: int = Field(
        ...,
        description="总运营商数量",
        examples=[150],
        ge=0
    )
    total_sessions: int = Field(
        ...,
        description="总游戏场次",
        examples=[5000],
        ge=0
    )
    total_players: int = Field(
        ...,
        description="总玩家人次",
        examples=[22500],
        ge=0
    )
    total_revenue: str = Field(
        ...,
        description="总收入(格式化为两位小数)",
        pattern=r'^\d+\.\d{2}$',
        examples=["225000.00"]
    )

    class Config:
        from_attributes = True


# ========== 多维度交叉分析 (T203) ==========

class CrossAnalysisRequest(BaseModel):
    """多维度交叉分析请求参数

    用于筛选和对比不同维度的统计数据。
    """

    dimension: DimensionType = Field(
        ...,
        description="分析维度: operator(运营商)/site(运营点)/application(应用)",
        examples=["operator"]
    )
    start_time: Optional[datetime] = Field(
        None,
        description="开始时间(ISO 8601格式)",
        examples=["2025-01-01T00:00:00Z"]
    )
    end_time: Optional[datetime] = Field(
        None,
        description="结束时间(ISO 8601格式)",
        examples=["2025-01-31T23:59:59Z"]
    )
    dimension_values: Optional[str] = Field(
        None,
        description="维度值筛选(逗号分隔的ID列表，用于只查看特定维度值的数据)",
        examples=["uuid1,uuid2,uuid3"]
    )

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, v, info):
        """验证时间范围合法性"""
        start_time = info.data.get("start_time")
        if start_time and v and v < start_time:
            raise ValueError("end_time must be after start_time")
        return v

    class Config:
        from_attributes = True


class CrossAnalysisItem(BaseModel):
    """多维度交叉分析的单个维度数据

    表示某个具体维度值（如某个运营商、某个应用）的统计数据。
    """

    dimension_id: str = Field(
        ...,
        description="维度值ID(运营商ID/运营点ID/应用ID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    dimension_name: str = Field(
        ...,
        description="维度值名称(运营商名称/运营点名称/应用名称)",
        examples=["北京朝阳运营商"]
    )
    total_sessions: int = Field(
        ...,
        description="总场次",
        examples=[120],
        ge=0
    )
    total_players: int = Field(
        ...,
        description="总玩家人次",
        examples=[540],
        ge=0
    )
    total_revenue: str = Field(
        ...,
        description="总收入(格式化为两位小数)",
        pattern=r'^\d+\.\d{2}$',
        examples=["5400.00"]
    )
    avg_players_per_session: float = Field(
        ...,
        description="平均每场玩家数",
        examples=[4.5],
        ge=0
    )

    class Config:
        from_attributes = True


class CrossAnalysisResponse(BaseModel):
    """多维度交叉分析响应

    返回按指定维度分组的统计数据列表，用于对比分析。
    """

    dimension: str = Field(
        ...,
        description="分析维度",
        examples=["operator"]
    )
    items: List[CrossAnalysisItem] = Field(
        ...,
        description="维度统计数据列表"
    )

    class Config:
        from_attributes = True
