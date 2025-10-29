"""全局统计服务 (T198)

提供管理员使用的全局统计数据查询功能：
- 全局仪表盘统计
- 多维度交叉分析
- 玩家数量分布统计
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID as PyUUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.operator_account import OperatorAccount
from ..models.usage_record import UsageRecord
from ..models.operation_site import OperationSite
from ..models.application import Application


class GlobalStatisticsService:
    """全局统计服务

    提供系统级别的数据聚合和分析功能。
    """

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def get_global_dashboard(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> dict:
        """获取全局统计仪表盘数据

        Args:
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            dict: 包含以下字段：
                - total_operators: 总运营商数
                - total_sessions: 总游戏场次
                - total_players: 总玩家人次
                - total_revenue: 总收入（字符串，两位小数）
        """
        # 1. 统计总运营商数（不受时间筛选影响，统计所有注册的运营商）
        operator_count_query = select(func.count(OperatorAccount.id))
        result = await self.db.execute(operator_count_query)
        total_operators = result.scalar_one()

        # 2. 构建时间筛选条件
        time_filters = []
        if start_time:
            time_filters.append(UsageRecord.created_at >= start_time)
        if end_time:
            time_filters.append(UsageRecord.created_at <= end_time)

        # 3. 统计游戏场次、玩家人次、总收入
        usage_stats_query = select(
            func.count(UsageRecord.id).label("total_sessions"),
            func.sum(UsageRecord.player_count).label("total_players"),
            func.sum(UsageRecord.total_cost).label("total_revenue")
        )

        if time_filters:
            usage_stats_query = usage_stats_query.where(and_(*time_filters))

        result = await self.db.execute(usage_stats_query)
        stats = result.first()

        total_sessions = stats.total_sessions if stats and stats.total_sessions else 0
        total_players = stats.total_players if stats and stats.total_players else 0
        total_revenue = stats.total_revenue if stats and stats.total_revenue else Decimal("0.00")

        return {
            "total_operators": total_operators,
            "total_sessions": total_sessions,
            "total_players": total_players,
            "total_revenue": f"{total_revenue:.2f}"
        }

    async def get_cross_analysis(
        self,
        dimension: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        dimension_values: Optional[List[PyUUID]] = None
    ) -> dict:
        """获取多维度交叉分析数据

        Args:
            dimension: 分析维度 (operator/site/application)
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            dimension_values: 维度值筛选（可选，UUID列表）

        Returns:
            dict: 包含dimension和items列表
        """
        # 1. 构建时间筛选条件
        time_filters = []
        if start_time:
            time_filters.append(UsageRecord.created_at >= start_time)
        if end_time:
            time_filters.append(UsageRecord.created_at <= end_time)

        # 2. 根据维度构建查询
        if dimension == "operator":
            dimension_id_field = UsageRecord.operator_id
            join_model = OperatorAccount
            join_condition = UsageRecord.operator_id == OperatorAccount.id
            name_field = OperatorAccount.full_name
        elif dimension == "site":
            dimension_id_field = UsageRecord.site_id
            join_model = OperationSite
            join_condition = UsageRecord.site_id == OperationSite.id
            name_field = OperationSite.name
        elif dimension == "application":
            dimension_id_field = UsageRecord.application_id
            join_model = Application
            join_condition = UsageRecord.application_id == Application.id
            name_field = Application.app_name
        else:
            raise ValueError(f"Invalid dimension: {dimension}")

        # 3. 添加维度值筛选
        if dimension_values:
            time_filters.append(dimension_id_field.in_(dimension_values))

        # 4. 构建分组聚合查询
        query = select(
            dimension_id_field.label("dimension_id"),
            name_field.label("dimension_name"),
            func.count(UsageRecord.id).label("total_sessions"),
            func.sum(UsageRecord.player_count).label("total_players"),
            func.sum(UsageRecord.total_cost).label("total_revenue")
        ).join(
            join_model,
            join_condition
        ).group_by(
            dimension_id_field,
            name_field
        ).order_by(
            func.sum(UsageRecord.total_cost).desc()  # 按收入降序排列
        )

        if time_filters:
            query = query.where(and_(*time_filters))

        # 5. 执行查询
        result = await self.db.execute(query)
        rows = result.all()

        # 6. 构建返回数据
        items = []
        for row in rows:
            total_sessions = row.total_sessions if row.total_sessions else 0
            total_players = row.total_players if row.total_players else 0
            total_revenue = row.total_revenue if row.total_revenue else Decimal("0.00")

            # 计算平均玩家数
            avg_players = float(total_players / total_sessions) if total_sessions > 0 else 0.0

            items.append({
                "dimension_id": str(row.dimension_id),
                "dimension_name": row.dimension_name,
                "total_sessions": total_sessions,
                "total_players": total_players,
                "total_revenue": f"{total_revenue:.2f}",
                "avg_players_per_session": round(avg_players, 2)
            })

        return {
            "dimension": dimension,
            "items": items
        }

    async def get_player_distribution(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> dict:
        """获取玩家数量分布统计

        Args:
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            dict: 包含distribution列表、total_sessions和most_common_player_count
        """
        # 1. 构建时间筛选条件
        time_filters = []
        if start_time:
            time_filters.append(UsageRecord.created_at >= start_time)
        if end_time:
            time_filters.append(UsageRecord.created_at <= end_time)

        # 2. 按玩家数量分组统计
        query = select(
            UsageRecord.player_count.label("player_count"),
            func.count(UsageRecord.id).label("session_count"),
            func.sum(UsageRecord.total_cost).label("total_revenue")
        ).group_by(
            UsageRecord.player_count
        ).order_by(
            UsageRecord.player_count
        )

        if time_filters:
            query = query.where(and_(*time_filters))

        result = await self.db.execute(query)
        rows = result.all()

        # 3. 计算总场次
        total_sessions = sum(row.session_count for row in rows) if rows else 0

        # 4. 找出最常见的玩家数量
        most_common_player_count = 0
        max_session_count = 0
        for row in rows:
            if row.session_count > max_session_count:
                max_session_count = row.session_count
                most_common_player_count = row.player_count

        # 5. 构建分布数据
        distribution = []
        for row in rows:
            session_count = row.session_count if row.session_count else 0
            total_revenue = row.total_revenue if row.total_revenue else Decimal("0.00")

            # 计算占比
            percentage = (session_count / total_sessions * 100) if total_sessions > 0 else 0.0

            distribution.append({
                "player_count": row.player_count,
                "session_count": session_count,
                "percentage": round(percentage, 2),
                "total_revenue": f"{total_revenue:.2f}"
            })

        return {
            "distribution": distribution,
            "total_sessions": total_sessions,
            "most_common_player_count": most_common_player_count if most_common_player_count > 0 else 4  # 默认4人
        }
