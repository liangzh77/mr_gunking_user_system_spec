"""统计分析相关的Pydantic Schemas (T108)

此模块定义统计分析的数据模型。
用于API响应和数据序列化。
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ========== 按运营点统计 (T112) ==========

class SiteStatisticsItem(BaseModel):
    """单个运营点的统计数据

    用于T112按运营点统计API的返回数据
    """

    site_id: str = Field(..., description="运营点ID", examples=["site_xxx"])
    site_name: str = Field(..., description="运营点名称", examples=["北京朝阳门店"])
    total_sessions: int = Field(..., description="总场次", examples=[60], ge=0)
    total_players: int = Field(..., description="总玩家数", examples=[270], ge=0)
    total_cost: str = Field(..., description="总消费金额", pattern=r'^\d+\.\d{2}$', examples=["2700.00"])

    class Config:
        from_attributes = True


class SiteStatisticsResponse(BaseModel):
    """按运营点统计响应"""

    sites: List[SiteStatisticsItem] = Field(..., description="运营点统计列表")


# ========== 按应用统计 (T113) ==========

class ApplicationStatisticsItem(BaseModel):
    """单个应用的统计数据

    用于T113按应用统计API的返回数据
    """

    app_id: str = Field(..., description="应用ID", examples=["app_xxx"])
    app_name: str = Field(..., description="应用名称", examples=["太空探险"])
    total_sessions: int = Field(..., description="总场次", examples=[80], ge=0)
    total_players: int = Field(..., description="总玩家数", examples=[360], ge=0)
    avg_players_per_session: float = Field(..., description="平均每场玩家数", examples=[4.5], ge=0)
    total_cost: str = Field(..., description="总消费金额", pattern=r'^\d+\.\d{2}$', examples=["3600.00"])

    class Config:
        from_attributes = True


class ApplicationStatisticsResponse(BaseModel):
    """按应用统计响应"""

    applications: List[ApplicationStatisticsItem] = Field(..., description="应用统计列表")


# ========== 按时间统计消费 (T114) ==========

class ChartDataPoint(BaseModel):
    """图表数据点

    按时间维度的单个数据点(day/week/month)
    """

    date: str = Field(..., description="日期(格式: YYYY-MM-DD或YYYY-Www或YYYY-MM)", examples=["2025-01-15"])
    total_sessions: int = Field(..., description="总场次", examples=[10], ge=0)
    total_players: int = Field(..., description="总玩家数", examples=[45], ge=0)
    total_cost: str = Field(..., description="总消费金额", pattern=r'^\d+\.\d{2}$', examples=["450.00"])

    class Config:
        from_attributes = True


class ConsumptionSummary(BaseModel):
    """消费汇总统计"""

    total_sessions: int = Field(..., description="总场次", examples=[100], ge=0)
    total_players: int = Field(..., description="总玩家数", examples=[450], ge=0)
    total_cost: str = Field(..., description="总消费金额", pattern=r'^\d+\.\d{2}$', examples=["4500.00"])
    avg_players_per_session: float = Field(..., description="平均每场玩家数", examples=[4.5], ge=0)

    class Config:
        from_attributes = True


class ConsumptionStatisticsResponse(BaseModel):
    """按时间统计消费响应"""

    dimension: str = Field(..., description="时间维度", examples=["day"], pattern="^(day|week|month)$")
    chart_data: List[ChartDataPoint] = Field(..., description="图表数据点列表")
    summary: ConsumptionSummary = Field(..., description="汇总统计")

    class Config:
        from_attributes = True


# ========== 玩家数量分布统计 (T115) ==========

class PlayerDistributionItem(BaseModel):
    """玩家数量分布项

    用于T115玩家数量分布统计API的返回数据
    """

    player_count: int = Field(..., description="玩家数量", examples=[4], ge=1, le=100)
    session_count: int = Field(..., description="该玩家数的场次", examples=[25], ge=0)
    percentage: float = Field(..., description="占比(%)", examples=[25.0], ge=0, le=100)
    total_cost: str = Field(..., description="该玩家数的总消费", pattern=r'^\d+\.\d{2}$', examples=["1000.00"])

    class Config:
        from_attributes = True


class PlayerDistributionResponse(BaseModel):
    """玩家数量分布统计响应"""

    distribution: List[PlayerDistributionItem] = Field(..., description="分布数据列表")
    total_sessions: int = Field(..., description="总场次", examples=[100], ge=0)
    most_common_player_count: int = Field(..., description="最常见的玩家数", examples=[4], ge=1)

    class Config:
        from_attributes = True


# ========== 通用统计请求参数 ==========

class StatisticsQueryParams(BaseModel):
    """统计查询通用参数

    用于筛选统计数据的时间范围
    """

    start_time: Optional[datetime] = Field(None, description="开始时间(ISO 8601格式)")
    end_time: Optional[datetime] = Field(None, description="结束时间(ISO 8601格式)")

    class Config:
        from_attributes = True
