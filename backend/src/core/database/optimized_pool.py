"""
优化的数据库连接池和查询管理

提供连接池监控、查询优化、读写分离等功能
"""
import asyncio
import time
import structlog
import json
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy import text, event
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import ClauseElement

from ..metrics.enhanced_metrics import record_database_query

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class QueryType(Enum):
    """查询类型"""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    DDL = "ddl"
    OTHER = "other"


@dataclass
class QueryMetrics:
    """查询指标"""
    query_type: QueryType
    table_name: str
    duration_ms: float
    rows_affected: int
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    sql_hash: Optional[str] = None


@dataclass
class PoolMetrics:
    """连接池指标"""
    pool_size: int
    checked_out: int
    checked_in: int
    overflow: int
    timestamp: datetime
    invalid: int = 0


class DatabaseConnectionPool:
    """优化的数据库连接池"""

    def __init__(self,
                 database_url: str,
                 pool_size: int = 20,
                 max_overflow: int = 10,
                 pool_timeout: int = 30,
                 pool_recycle: int = 3600,
                 pool_pre_ping: bool = True,
                 echo: bool = False):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo = echo

        self.engine: Optional[AsyncEngine] = None
        self.query_metrics: List[QueryMetrics] = []
        self.pool_metrics: List[PoolMetrics] = []
        self._max_metrics_history = 10000
        self._slow_query_threshold = 1000  # 毫秒

    async def initialize(self):
        """初始化连接池"""
        try:
            self.engine = create_async_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=self.pool_pre_ping,
                echo=self.echo,
                # 连接池事件监听
                connect_args={
                    "command_timeout": 60,
                    "server_settings": {
                        "application_name": "mr_gaming_system"
                    }
                }
            )

            # 注册事件监听器
            self._register_listeners()

            # 测试连接
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            logger.info("database_pool_initialized",
                       pool_size=self.pool_size,
                       max_overflow=self.max_overflow)

        except Exception as e:
            logger.error("database_pool_init_error", error=str(e))
            raise

    def _register_listeners(self):
        """注册事件监听器"""
        if not self.engine:
            return

        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """查询开始前记录"""
            context._query_start_time = time.time()

        @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """查询完成后记录指标"""
            if hasattr(context, '_query_start_time'):
                duration_ms = (time.time() - context._query_start_time) * 1000
                query_type = self._detect_query_type(statement)
                table_name = self._extract_table_name(statement)

                # 创建查询指标
                query_metrics = QueryMetrics(
                    query_type=query_type,
                    table_name=table_name,
                    duration_ms=duration_ms,
                    rows_affected=getattr(cursor, 'rowcount', 0),
                    timestamp=datetime.now(),
                    success=True,
                    sql_hash=self._hash_sql(statement)
                )

                self.query_metrics.append(query_metrics)
                self._cleanup_old_metrics()

                # 记录到Prometheus
                record_database_query(query_type.value, table_name, duration_ms / 1000)

                # 慢查询日志
                if duration_ms > self._slow_query_threshold:
                    logger.warning("slow_query_detected",
                               query_type=query_type.value,
                               table_name=table_name,
                               duration_ms=duration_ms,
                               sql_hash=query_metrics.sql_hash)

        @event.listens_for(self.engine.sync_engine, "handle_error")
        def handle_error(exception_context):
            """错误处理"""
            context = exception_context.execution_context
            if hasattr(context, '_query_start_time'):
                duration_ms = (time.time() - context._query_start_time) * 1000
                query_type = self._detect_query_type(context.statement)
                table_name = self._extract_table_name(context.statement)

                error_metrics = QueryMetrics(
                    query_type=query_type,
                    table_name=table_name,
                    duration_ms=duration_ms,
                    rows_affected=0,
                    timestamp=datetime.now(),
                    success=False,
                    error_message=str(exception_context.exception),
                    sql_hash=self._hash_sql(context.statement)
                )

                self.query_metrics.append(error_metrics)
                self._cleanup_old_metrics()

                logger.error("database_query_error",
                           query_type=query_type.value,
                           table_name=table_name,
                           duration_ms=duration_ms,
                           error=str(exception_context.exception))

        # 连接池状态监控
        @event.listens_for(self.engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接检出"""
            self._update_pool_metrics()

        @event.listens_for(self.engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record, connection_proxy):
            """连接检入"""
            self._update_pool_metrics()

    def _detect_query_type(self, statement: str) -> QueryType:
        """检测查询类型"""
        statement_upper = statement.strip().upper()

        if statement_upper.startswith('SELECT'):
            return QueryType.SELECT
        elif statement_upper.startswith('INSERT'):
            return QueryType.INSERT
        elif statement_upper.startswith('UPDATE'):
            return QueryType.UPDATE
        elif statement_upper.startswith('DELETE'):
            return QueryType.DELETE
        elif any(statement_upper.startswith(ddl) for ddl in ['CREATE', 'ALTER', 'DROP']):
            return QueryType.DDL
        else:
            return QueryType.OTHER

    def _extract_table_name(self, statement: str) -> str:
        """提取表名"""
        try:
            statement_upper = statement.strip().upper()

            if statement_upper.startswith('SELECT'):
                # FROM table_name
                if 'FROM' in statement_upper:
                    from_pos = statement_upper.index('FROM')
                    from_clause = statement[from_pos + 5:].strip()
                    # 提取第一个表名
                    table_name = from_clause.split()[0].strip('`"[]')
                    return table_name
            elif statement_upper.startswith('INSERT'):
                # INSERT INTO table_name
                if 'INTO' in statement_upper:
                    into_pos = statement_upper.index('INTO')
                    into_clause = statement[into_pos + 4:].strip()
                    table_name = into_clause.split()[0].strip('`"[]')
                    return table_name
            elif statement_upper.startswith('UPDATE'):
                # UPDATE table_name
                update_pos = statement_upper.index('UPDATE')
                update_clause = statement[update_pos + 6:].strip()
                table_name = update_clause.split()[0].strip('`"[]')
                return table_name
            elif statement_upper.startswith('DELETE'):
                # DELETE FROM table_name
                if 'FROM' in statement_upper:
                    from_pos = statement_upper.index('FROM')
                    from_clause = statement[from_pos + 5:].strip()
                    table_name = from_clause.split()[0].strip('`"[]')
                    return table_name

        except Exception:
            pass

        return "unknown"

    def _hash_sql(self, statement: str) -> str:
        """生成SQL语句的哈希值"""
        # 简化SQL语句（移除参数值）
        import re
        simplified = re.sub(r"'[^']*'", "'?'", statement)  # 替换字符串参数
        simplified = re.sub(r'\b\d+\b', '?', simplified)  # 替换数字参数
        return hashlib.md5(simplified.encode()).hexdigest()[:16]

    def _update_pool_metrics(self):
        """更新连接池指标"""
        if not self.engine:
            return

        pool = self.engine.pool
        metrics = PoolMetrics(
            pool_size=pool.size(),
            checked_out=pool.checkedout(),
            checked_in=pool.checkedin(),
            overflow=pool.overflow(),
            timestamp=datetime.now()
        )

        self.pool_metrics.append(metrics)
        if len(self.pool_metrics) > self._max_metrics_history:
            self.pool_metrics = self.pool_metrics[-self._max_metrics_history:]

    def _cleanup_old_metrics(self):
        """清理旧的指标数据"""
        if len(self.query_metrics) > self._max_metrics_history:
            self.query_metrics = self.query_metrics[-self._max_metrics_history:]

    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """获取数据库会话"""
        if not self.engine:
            raise RuntimeError("Database pool not initialized")

        async with AsyncSession(self.engine) as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """执行查询并返回结果"""
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            if result.returns_rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
            return []

    async def execute_scalar(self, query: str, params: Optional[Dict] = None) -> Any:
        """执行查询并返回单个值"""
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            row = result.first()
            return row[0] if row else None

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            start_time = time.time()
            await self.execute_scalar("SELECT 1")
            response_time = (time.time() - start_time) * 1000

            pool_status = self.get_pool_status()

            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'pool_status': pool_status,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        if not self.engine:
            return {'status': 'not_initialized'}

        pool = self.engine.pool
        return {
            'size': pool.size(),
            'checked_out': pool.checkedout(),
            'checked_in': pool.checkedin(),
            'overflow': pool.overflow(),
            'invalid': getattr(pool, 'invalid', 0),
            'utilization_rate': pool.checkedout() / pool.size() if pool.size() > 0 else 0
        }

    def get_query_statistics(self, minutes: int = 60) -> Dict[str, Any]:
        """获取查询统计信息"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_queries = [
            q for q in self.query_metrics
            if q.timestamp >= cutoff_time
        ]

        if not recent_queries:
            return {
                'period_minutes': minutes,
                'total_queries': 0,
                'message': 'No queries in the specified period'
            }

        # 基础统计
        total_queries = len(recent_queries)
        successful_queries = len([q for q in recent_queries if q.success])
        failed_queries = total_queries - successful_queries

        # 性能统计
        durations = [q.duration_ms for q in recent_queries]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0

        # 计算百分位数
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        p50 = sorted_durations[n // 2] if n > 0 else 0
        p95 = sorted_durations[int(n * 0.95)] if n > 0 else 0
        p99 = sorted_durations[int(n * 0.99)] if n > 0 else 0

        # 按查询类型分组
        queries_by_type = {}
        for query in recent_queries:
            query_type = query.query_type.value
            if query_type not in queries_by_type:
                queries_by_type[query_type] = {
                    'count': 0,
                    'success_count': 0,
                    'total_duration': 0,
                    'max_duration': 0,
                    'tables': set()
                }

            stats = queries_by_type[query_type]
            stats['count'] += 1
            if query.success:
                stats['success_count'] += 1
            stats['total_duration'] += query.duration_ms
            stats['max_duration'] = max(stats['max_duration'], query.duration_ms)
            stats['tables'].add(query.table_name)

        # 按表名分组
        queries_by_table = {}
        for query in recent_queries:
            table = query.table_name
            if table not in queries_by_table:
                queries_by_table[table] = {
                    'count': 0,
                    'total_duration': 0,
                    'avg_duration': 0,
                    'query_types': set()
                }

            stats = queries_by_table[table]
            stats['count'] += 1
            stats['total_duration'] += query.duration_ms
            stats['avg_duration'] = stats['total_duration'] / stats['count']
            stats['query_types'].add(query.query_type.value)

        # 慢查询
        slow_queries = [
            {
                'table_name': q.table_name,
                'query_type': q.query_type.value,
                'duration_ms': q.duration_ms,
                'timestamp': q.timestamp.isoformat(),
                'sql_hash': q.sql_hash
            }
            for q in recent_queries
            if q.duration_ms > self._slow_query_threshold
        ]

        return {
            'period_minutes': minutes,
            'total_queries': total_queries,
            'successful_queries': successful_queries,
            'failed_queries': failed_queries,
            'success_rate': successful_queries / total_queries if total_queries > 0 else 0,
            'performance': {
                'avg_duration_ms': avg_duration,
                'max_duration_ms': max_duration,
                'min_duration_ms': min_duration,
                'p50_duration_ms': p50,
                'p95_duration_ms': p95,
                'p99_duration_ms': p99
            },
            'queries_by_type': {
                query_type: {
                    'count': stats['count'],
                    'success_rate': stats['success_count'] / stats['count'] if stats['count'] > 0 else 0,
                    'avg_duration_ms': stats['total_duration'] / stats['count'] if stats['count'] > 0 else 0,
                    'max_duration_ms': stats['max_duration'],
                    'tables': list(stats['tables'])
                }
                for query_type, stats in queries_by_type.items()
            },
            'queries_by_table': {
                table: {
                    'count': stats['count'],
                    'avg_duration_ms': stats['avg_duration'],
                    'query_types': list(stats['query_types'])
                }
                for table, stats in queries_by_table.items()
            },
            'slow_queries_count': len(slow_queries),
            'slow_queries': sorted(slow_queries, key=lambda x: x['duration_ms'], reverse=True)[:10]
        }

    def get_pool_statistics(self, minutes: int = 60) -> Dict[str, Any]:
        """获取连接池统计信息"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.pool_metrics
            if m.timestamp >= cutoff_time
        ]

        if not recent_metrics:
            return {
                'period_minutes': minutes,
                'message': 'No pool metrics in the specified period'
            }

        # 连接池使用率统计
        utilization_rates = [
            (m.checked_out / m.pool_size) * 100 if m.pool_size > 0 else 0
            for m in recent_metrics
        ]

        return {
            'period_minutes': minutes,
            'current_status': self.get_pool_status(),
            'statistics': {
                'avg_utilization_percent': sum(utilization_rates) / len(utilization_rates),
                'max_utilization_percent': max(utilization_rates),
                'min_utilization_percent': min(utilization_rates),
                'avg_pool_size': sum(m.pool_size for m in recent_metrics) / len(recent_metrics),
                'avg_overflow': sum(m.overflow for m in recent_metrics) / len(recent_metrics)
            }
        }

    async def close(self):
        """关闭连接池"""
        if self.engine:
            await self.engine.dispose()
            logger.info("database_pool_closed")


class QueryOptimizer:
    """查询优化器"""

    def __init__(self, db_pool: DatabaseConnectionPool):
        self.db_pool = db_pool
        self._query_cache: Dict[str, Dict] = {}
        self._index_recommendations: Dict[str, List[str]] = {}

    async def analyze_slow_queries(self, hours: int = 24) -> Dict[str, Any]:
        """分析慢查询"""
        try:
            # PostgreSQL查询分析
            slow_queries_sql = """
            SELECT
                query,
                calls,
                total_exec_time,
                mean_exec_time,
                rows,
                100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
            FROM pg_stat_statements
            WHERE mean_exec_time > 100
            ORDER BY mean_exec_time DESC
            LIMIT 20;
            """

            slow_queries = await self.db_pool.execute_query(slow_queries_sql)

            # 缺失索引建议
            missing_indexes_sql = """
            SELECT
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation
            FROM pg_stats
            WHERE schemaname = 'public'
            AND correlation < 0.1
            AND n_distinct > 100
            ORDER BY n_distinct DESC;
            """

            potential_indexes = await self.db_pool.execute_query(missing_indexes_sql)

            # 表大小分析
            table_sizes_sql = """
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY size_bytes DESC;
            """

            table_sizes = await self.db_pool.execute_query(table_sizes_sql)

            return {
                'slow_queries': slow_queries,
                'potential_indexes': potential_indexes,
                'table_sizes': table_sizes,
                'recommendations': self._generate_optimization_recommendations(
                    slow_queries, potential_indexes, table_sizes
                )
            }

        except Exception as e:
            logger.error("query_analysis_error", error=str(e))
            return {'error': str(e)}

    def _generate_optimization_recommendations(self,
                                                slow_queries: List[Dict],
                                                potential_indexes: List[Dict],
                                                table_sizes: List[Dict]) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 基于慢查询的建议
        if slow_queries:
            recommendations.append(
                f"发现 {len(slow_queries)} 个慢查询，建议检查查询计划和索引"
            )

            # 分析最慢的查询
            slowest = slow_queries[0] if slow_queries else None
            if slowest and float(slowest.get('mean_exec_time', 0)) > 1000:
                recommendations.append(
                    f"最慢查询平均耗时 {slowest.get('mean_exec_time', 0):.2f}ms，强烈建议优化"
                )

        # 基于索引的建议
        if potential_indexes:
            recommendations.append(
                f"发现 {len(potential_indexes)} 个列可能需要索引以提高查询性能"
            )

        # 基于表大小的建议
        large_tables = [t for t in table_sizes if int(t.get('size_bytes', 0)) > 100 * 1024 * 1024]  # 100MB
        if large_tables:
            recommendations.append(
                f"发现 {len(large_tables)} 个大表，建议考虑分区或索引优化"
            )

        # 通用建议
        if not recommendations:
            recommendations.append("查询性能良好，无需立即优化")

        return recommendations

    async def create_index_recommendation(self, table: str, columns: List[str]) -> str:
        """创建索引建议"""
        index_name = f"idx_{table}_{'_'.join(columns)}"
        columns_str = ', '.join(columns)
        return f"CREATE INDEX CONCURRENTLY {index_name} ON {table} ({columns_str});"

    async def explain_query(self, query: str) -> Dict[str, Any]:
        """分析查询执行计划"""
        try:
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            result = await self.db_pool.execute_scalar(explain_query)

            if result:
                plan_data = json.loads(result) if isinstance(result, str) else result
                return self._analyze_execution_plan(plan_data)

            return {'error': 'No execution plan returned'}

        except Exception as e:
            logger.error("query_explain_error", error=str(e))
            return {'error': str(e)}

    def _analyze_execution_plan(self, plan_data: Any) -> Dict[str, Any]:
        """分析执行计划"""
        analysis = {
            'total_cost': 0,
            'planning_time': 0,
            'execution_time': 0,
            'rows_removed': 0,
            'uses_index': False,
            'recommendations': []
        }

        try:
            if isinstance(plan_data, list) and plan_data:
                plan = plan_data[0]
            else:
                plan = plan_data

            if isinstance(plan, dict):
                analysis['total_cost'] = plan.get('Total Cost', 0)
                analysis['planning_time'] = plan.get('Planning Time', 0)
                analysis['execution_time'] = plan.get('Execution Time', 0)

                # 检查是否使用了索引
                plan_str = json.dumps(plan)
                if 'Index Scan' in plan_str or 'Index Only Scan' in plan_str:
                    analysis['uses_index'] = True
                else:
                    analysis['recommendations'].append('考虑添加适当的索引以提高查询性能')

                # 检查是否有顺序扫描
                if 'Seq Scan' in plan_str:
                    analysis['recommendations'].append('使用了顺序扫描，对于大表可能效率较低')

        except Exception as e:
            logger.error("execution_plan_analysis_error", error=str(e))

        return analysis


# 全局数据库连接池实例
_db_pool: Optional[DatabaseConnectionPool] = None
_query_optimizer: Optional[QueryOptimizer] = None


def get_db_pool() -> DatabaseConnectionPool:
    """获取数据库连接池实例"""
    global _db_pool
    if _db_pool is None:
        raise RuntimeError("Database pool not initialized")
    return _db_pool


def get_query_optimizer() -> QueryOptimizer:
    """获取查询优化器实例"""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer(get_db_pool())
    return _query_optimizer


async def init_database_pool(database_url: str, **kwargs) -> DatabaseConnectionPool:
    """初始化数据库连接池"""
    global _db_pool, _query_optimizer

    _db_pool = DatabaseConnectionPool(database_url, **kwargs)
    await _db_pool.initialize()

    _query_optimizer = QueryOptimizer(_db_pool)

    logger.info("database_pool_and_optimizer_initialized")
    return _db_pool


async def close_database_pool():
    """关闭数据库连接池"""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("database_pool_closed")