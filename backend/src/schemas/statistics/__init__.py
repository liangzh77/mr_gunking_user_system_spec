"""Statistics schemas package

全局统计相关的Schema定义
"""

# 使用importlib导入global模块（因为global是Python关键字）
import importlib
_global_module = importlib.import_module('.global', package='src.schemas.statistics')

GlobalDashboardResponse = _global_module.GlobalDashboardResponse
CrossAnalysisRequest = _global_module.CrossAnalysisRequest
CrossAnalysisItem = _global_module.CrossAnalysisItem
CrossAnalysisResponse = _global_module.CrossAnalysisResponse

# 导入玩家分布统计schemas
from .player_distribution import (
    PlayerDistributionItem,
    PlayerDistributionResponse,
)

__all__ = [
    "GlobalDashboardResponse",
    "CrossAnalysisRequest",
    "CrossAnalysisItem",
    "CrossAnalysisResponse",
    "PlayerDistributionItem",
    "PlayerDistributionResponse",
]
