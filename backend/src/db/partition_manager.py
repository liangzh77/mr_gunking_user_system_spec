"""数据库分区自动管理模块.

该模块负责自动创建和维护PostgreSQL分区表，确保分区表始终可用。

主要功能:
1. 启动时自动创建未来N个月的分区
2. 定时任务每月自动维护分区
3. 支持多个分区表的统一管理

分区表列表:
- finance_operation_logs: 财务操作日志（按月分区）
"""

from datetime import datetime, timedelta
from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .session import get_db_session
from ..core import get_logger

logger = get_logger(__name__)


class PartitionManager:
    """分区表管理器."""

    # 需要管理的分区表配置
    PARTITION_TABLES = [
        {
            "table_name": "finance_operation_logs",
            "partition_key": "created_at",
            "partition_type": "monthly",  # 按月分区
        },
        # 未来可以添加更多分区表
        # {
        #     "table_name": "game_sessions",
        #     "partition_key": "session_start",
        #     "partition_type": "monthly",
        # },
    ]

    def __init__(self, db: AsyncSession):
        """初始化分区管理器.

        Args:
            db: 数据库会话
        """
        self.db = db

    async def ensure_partitions(self, months_ahead: int = 6) -> None:
        """确保分区表存在（创建当前月及未来N个月的分区）.

        Args:
            months_ahead: 提前创建多少个月的分区（默认6个月）
        """
        logger.info(
            "partition_check_started",
            months_ahead=months_ahead,
            tables=len(self.PARTITION_TABLES),
        )

        for table_config in self.PARTITION_TABLES:
            await self._ensure_table_partitions(table_config, months_ahead)

        logger.info("partition_check_completed", months_ahead=months_ahead)

    async def _ensure_table_partitions(
        self, table_config: dict, months_ahead: int
    ) -> None:
        """为单个表创建分区.

        Args:
            table_config: 分区表配置
            months_ahead: 提前创建多少个月
        """
        table_name = table_config["table_name"]
        partition_type = table_config["partition_type"]

        if partition_type == "monthly":
            await self._create_monthly_partitions(table_name, months_ahead)
        else:
            logger.warning(
                "unsupported_partition_type",
                table_name=table_name,
                partition_type=partition_type,
            )

    async def _create_monthly_partitions(
        self, table_name: str, months_ahead: int
    ) -> None:
        """创建月度分区.

        Args:
            table_name: 分区表名称
            months_ahead: 提前创建多少个月
        """
        today = datetime.utcnow().date()
        current_month_start = datetime(today.year, today.month, 1)

        created_count = 0
        skipped_count = 0

        # 创建当前月和未来N个月的分区
        for i in range(months_ahead + 1):
            partition_start = self._add_months(current_month_start, i)
            partition_end = self._add_months(partition_start, 1)

            partition_name = f"{table_name}_{partition_start.strftime('%Y_%m')}"

            # 检查分区是否已存在
            exists = await self._partition_exists(partition_name)

            if exists:
                logger.debug(
                    "partition_already_exists",
                    table_name=table_name,
                    partition_name=partition_name,
                    partition_start=partition_start.strftime("%Y-%m-%d"),
                )
                skipped_count += 1
                continue

            # 创建分区
            try:
                await self._create_partition(
                    table_name=table_name,
                    partition_name=partition_name,
                    partition_start=partition_start,
                    partition_end=partition_end,
                )
                created_count += 1
                logger.info(
                    "partition_created",
                    table_name=table_name,
                    partition_name=partition_name,
                    partition_start=partition_start.strftime("%Y-%m-%d"),
                    partition_end=partition_end.strftime("%Y-%m-%d"),
                )
            except Exception as e:
                logger.error(
                    "partition_creation_failed",
                    table_name=table_name,
                    partition_name=partition_name,
                    error=str(e),
                    exc_info=True,
                )
                # 继续创建其他分区，不中断流程

        logger.info(
            "monthly_partitions_summary",
            table_name=table_name,
            created=created_count,
            skipped=skipped_count,
            total=months_ahead + 1,
        )

    async def _partition_exists(self, partition_name: str) -> bool:
        """检查分区表是否存在.

        Args:
            partition_name: 分区表名称

        Returns:
            bool: 分区是否存在
        """
        query = text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_tables
                WHERE tablename = :partition_name
            )
        """)

        result = await self.db.execute(query, {"partition_name": partition_name})
        return result.scalar()

    async def _create_partition(
        self,
        table_name: str,
        partition_name: str,
        partition_start: datetime,
        partition_end: datetime,
    ) -> None:
        """创建分区表.

        Args:
            table_name: 主表名称
            partition_name: 分区表名称
            partition_start: 分区起始时间
            partition_end: 分区结束时间
        """
        # 格式化日期为 PostgreSQL 可识别的格式
        start_str = partition_start.strftime("%Y-%m-%d")
        end_str = partition_end.strftime("%Y-%m-%d")

        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF {table_name}
            FOR VALUES FROM ('{start_str}') TO ('{end_str}')
        """

        await self.db.execute(text(create_sql))
        await self.db.commit()

    @staticmethod
    def _add_months(source_date: datetime, months: int) -> datetime:
        """给日期增加指定月数.

        Args:
            source_date: 源日期
            months: 要增加的月数

        Returns:
            datetime: 新日期
        """
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1
        return datetime(year, month, 1)


async def ensure_partitions(months_ahead: int = 6) -> None:
    """确保所有分区表存在（便捷函数）.

    这个函数会自动获取数据库会话并创建分区。
    适用于在应用启动时或定时任务中调用。

    Args:
        months_ahead: 提前创建多少个月的分区（默认6个月）
    """
    try:
        async for db in get_db_session():
            manager = PartitionManager(db)
            await manager.ensure_partitions(months_ahead)
            break  # 只执行一次
    except Exception as e:
        logger.error(
            "partition_maintenance_failed",
            error=str(e),
            exc_info=True,
        )
        # 不抛出异常，避免影响应用启动
        # 分区问题应该记录日志，但不应该阻止应用启动
