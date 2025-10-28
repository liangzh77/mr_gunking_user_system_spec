"""
数据库优化模块

提供查询优化、索引建议、连接池优化等功能
"""
import asyncio
import time
import structlog
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..database.optimized_pool import get_db_pool
from ..cache.enhanced_cache import get_multi_cache

logger = structlog.get_logger(__name__)


@dataclass
class QueryPerformanceStats:
    """查询性能统计"""
    query_hash: str
    query_template: str
    execution_count: int
    total_duration: float
    avg_duration: float
    max_duration: float
    min_duration: float
    slow_count: int
    last_executed: datetime
    error_count: int


@dataclass
class IndexRecommendation:
    """索引建议"""
    table_name: str
    column_names: List[str]
    index_type: str
    estimated_impact: str
    current_usage: Optional[Dict[str, Any]] = None
    creation_sql: Optional[str] = None


@dataclass
class TableStatistics:
    """表统计信息"""
    table_name: str
    row_count: int
    table_size: int
    index_size: int
    last_analyzed: datetime
    fragmentation_level: float
    recommended_actions: List[str]


class DatabaseOptimizer:
    """数据库优化器"""

    def __init__(self):
        self.db_pool = get_db_pool()
        self.cache = get_multi_cache()
        self._query_stats: Dict[str, QueryPerformanceStats] = {}
        self._index_recommendations: Dict[str, List[IndexRecommendation]] = {}
        self._table_stats: Dict[str, TableStatistics] = {}
        self._slow_query_threshold = 1.0  # 秒
        self._max_stats_entries = 10000

    async def analyze_query_performance(self, query: str, duration: float,
                                     success: bool = True, error: str = None) -> str:
        """分析查询性能"""
        query_hash = self._generate_query_hash(query)

        if query_hash not in self._query_stats:
            self._query_stats[query_hash] = QueryPerformanceStats(
                query_hash=query_hash,
                query_template=self._extract_query_template(query),
                execution_count=0,
                total_duration=0.0,
                avg_duration=0.0,
                max_duration=0.0,
                min_duration=float('inf'),
                slow_count=0,
                last_executed=datetime.now(),
                error_count=0
            )

        stats = self._query_stats[query_hash]
        stats.execution_count += 1
        stats.total_duration += duration
        stats.avg_duration = stats.total_duration / stats.execution_count
        stats.max_duration = max(stats.max_duration, duration)
        stats.min_duration = min(stats.min_duration, duration)
        stats.last_executed = datetime.now()

        if duration > self._slow_query_threshold:
            stats.slow_count += 1
            logger.warning("slow_query_detected",
                         query_template=stats.query_template,
                         duration=duration,
                         threshold=self._slow_query_threshold)

        if not success:
            stats.error_count += 1
            logger.error("query_execution_failed",
                        query_template=stats.query_template,
                        error=error)

        # 缓存查询统计
        await self.cache.set(f"query_stats:{query_hash}", stats, ttl=3600)

        return query_hash

    def _generate_query_hash(self, query: str) -> str:
        """生成查询哈希"""
        import hashlib
        normalized_query = ' '.join(query.lower().split())
        return hashlib.md5(normalized_query.encode()).hexdigest()

    def _extract_query_template(self, query: str) -> str:
        """提取查询模板"""
        import re

        # 移除具体的值，保留模板
        template = re.sub(r"'[^']*'", "'?'", query)  # 字符串值
        template = re.sub(r'\b\d+\b', '?', template)  # 数字值
        template = re.sub(r'\s+', ' ', template).strip()

        return template

    async def get_slow_queries(self, hours: int = 24,
                             min_count: int = 5) -> List[QueryPerformanceStats]:
        """获取慢查询列表"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        slow_queries = []
        for stats in self._query_stats.values():
            if (stats.last_executed >= cutoff_time and
                stats.slow_count >= min_count and
                stats.avg_duration > self._slow_query_threshold):
                slow_queries.append(stats)

        # 按平均执行时间排序
        slow_queries.sort(key=lambda x: x.avg_duration, reverse=True)
        return slow_queries

    async def analyze_table_usage(self) -> Dict[str, TableStatistics]:
        """分析表使用情况"""
        try:
            async with self.db_pool.get_connection() as conn:
                # 获取所有表的统计信息
                tables_query = """
                SELECT
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                """

                result = await conn.execute(tables_query)
                tables_data = result.fetchall()

                # 获取表大小信息
                table_sizes_query = """
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                                  pg_relation_size(schemaname||'.'||tablename)) as index_size
                FROM pg_tables
                WHERE schemaname = 'public'
                """

                size_result = await conn.execute(table_sizes_query)
                size_data = size_result.fetchall()

                # 合并统计信息
                table_stats = {}
                for table_info in tables_data:
                    table_name = table_info['tablename']

                    # 查找对应的表大小信息
                    size_info = next((s for s in size_data if s['tablename'] == table_name), None)

                    # 计算碎片化程度
                    live_tuples = table_info['live_tuples']
                    dead_tuples = table_info['dead_tuples']
                    fragmentation = dead_tuples / (live_tuples + dead_tuples) if (live_tuples + dead_tuples) > 0 else 0

                    # 生成推荐操作
                    recommendations = []
                    if fragmentation > 0.2:
                        recommendations.append("建议执行VACUUM清理死元组")
                    if not table_info['last_analyze']:
                        recommendations.append("建议执行ANALYZE更新统计信息")
                    if dead_tuples > live_tuples * 0.5:
                        recommendations.append("死元组过多，建议频繁执行VACUUM")

                    stats = TableStatistics(
                        table_name=table_name,
                        row_count=live_tuples,
                        table_size=self._parse_size(size_info['table_size'] if size_info else '0'),
                        index_size=self._parse_size(size_info['index_size'] if size_info else '0'),
                        last_analyzed=table_info['last_analyze'] or datetime.min,
                        fragmentation_level=fragmentation,
                        recommended_actions=recommendations
                    )

                    table_stats[table_name] = stats

                self._table_stats = table_stats

                # 缓存统计信息
                await self.cache.set("table_statistics", table_stats, ttl=1800)

                logger.info("table_usage_analysis_completed",
                          tables_count=len(table_stats))

                return table_stats

        except Exception as e:
            logger.error("table_usage_analysis_failed", error=str(e))
            return {}

    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串为字节数"""
        if not size_str:
            return 0

        size_str = size_str.strip().upper()
        if size_str.endswith('KB'):
            return int(float(size_str[:-2]) * 1024)
        elif size_str.endswith('MB'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        elif size_str.endswith('GB'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
        else:
            return int(size_str)

    async def generate_index_recommendations(self) -> Dict[str, List[IndexRecommendation]]:
        """生成索引建议"""
        try:
            async with self.db_pool.get_connection() as conn:
                # 获取未使用的索引
                unused_indexes_query = """
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as index_scans
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                AND schemaname = 'public'
                """

                result = await conn.execute(unused_indexes_query)
                unused_indexes = result.fetchall()

                # 获取可能缺失索引的查询
                missing_indexes_query = """
                SELECT
                    query,
                    calls,
                    total_exec_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements
                WHERE query LIKE '%SELECT%'
                AND calls > 10
                AND total_exec_time > 1000
                ORDER BY total_exec_time DESC
                LIMIT 20
                """

                try:
                    missing_result = await conn.execute(missing_indexes_query)
                    slow_queries = missing_result.fetchall()
                except Exception:
                    # pg_stat_statements可能未启用
                    slow_queries = []

                recommendations = {}

                # 分析未使用的索引
                for index_info in unused_indexes:
                    table_name = index_info['tablename']
                    if table_name not in recommendations:
                        recommendations[table_name] = []

                    recommendations[table_name].append(IndexRecommendation(
                        table_name=table_name,
                        column_names=[index_info['indexname']],
                        index_type="unused",
                        estimated_impact="建议删除，从未被使用",
                        current_usage={"scans": 0}
                    ))

                # 分析慢查询生成索引建议
                for query_info in slow_queries:
                    query = query_info['query']
                    # 简单的WHERE子句解析（实际实现中需要更复杂的SQL解析）
                    if 'WHERE' in query.upper():
                        # 这里应该解析WHERE子句中的列
                        # 简化实现，实际需要SQL解析器
                        pass

                self._index_recommendations = recommendations

                # 缓存索引建议
                await self.cache.set("index_recommendations", recommendations, ttl=3600)

                logger.info("index_recommendations_generated",
                          tables_count=len(recommendations),
                          total_recommendations=sum(len(recs) for recs in recommendations.values()))

                return recommendations

        except Exception as e:
            logger.error("index_recommendations_failed", error=str(e))
            return {}

    async def optimize_connection_pool(self) -> Dict[str, Any]:
        """优化连接池设置"""
        try:
            pool_stats = self.db_pool.get_pool_status()

            recommendations = []

            # 分析连接池利用率
            if pool_stats['utilization_rate'] > 0.8:
                recommendations.append({
                    "issue": "连接池利用率过高",
                    "current_value": pool_stats['utilization_rate'],
                    "recommended_value": "< 0.8",
                    "action": "建议增加连接池大小"
                })

            if pool_stats['wait_count'] > 0:
                recommendations.append({
                    "issue": "存在连接等待",
                    "current_value": pool_stats['wait_count'],
                    "recommended_value": 0,
                    "action": "建议增加连接池大小或优化查询"
                })

            # 分析查询性能
            slow_queries = await self.get_slow_queries()
            if slow_queries:
                recommendations.append({
                    "issue": "存在慢查询",
                    "current_value": len(slow_queries),
                    "recommended_value": 0,
                    "action": "建议优化慢查询或添加索引"
                })

            optimization_report = {
                "current_pool_stats": pool_stats,
                "slow_queries_count": len(slow_queries),
                "recommendations": recommendations,
                "optimization_score": self._calculate_optimization_score(pool_stats, slow_queries),
                "timestamp": datetime.now().isoformat()
            }

            logger.info("connection_pool_optimization_completed",
                        recommendations_count=len(recommendations),
                        optimization_score=optimization_report["optimization_score"])

            return optimization_report

        except Exception as e:
            logger.error("connection_pool_optimization_failed", error=str(e))
            return {"error": str(e)}

    def _calculate_optimization_score(self, pool_stats: Dict[str, Any],
                                   slow_queries: List) -> float:
        """计算优化评分"""
        score = 100.0

        # 连接池利用率影响
        if pool_stats['utilization_rate'] > 0.8:
            score -= 20
        elif pool_stats['utilization_rate'] > 0.6:
            score -= 10

        # 等待连接影响
        if pool_stats['wait_count'] > 0:
            score -= 15

        # 慢查询影响
        slow_query_penalty = min(len(slow_queries) * 2, 30)
        score -= slow_query_penalty

        return max(score, 0)

    async def get_optimization_report(self) -> Dict[str, Any]:
        """获取综合优化报告"""
        try:
            # 获取各种统计信息
            table_stats = await self.analyze_table_usage()
            index_recommendations = await self.generate_index_recommendations()
            slow_queries = await self.get_slow_queries()
            pool_optimization = await self.optimize_connection_pool()

            # 计算总体健康评分
            health_score = self._calculate_health_score(
                table_stats, index_recommendations, slow_queries, pool_optimization
            )

            # 生成关键建议
            critical_issues = []

            if len(slow_queries) > 5:
                critical_issues.append(f"发现{len(slow_queries)}个慢查询，需要优化")

            total_unused_indexes = sum(len(recs) for recs in index_recommendations.values()
                                     if any(r.index_type == "unused" for r in recs))
            if total_unused_indexes > 3:
                critical_issues.append(f"发现{total_unused_indexes}个未使用的索引，建议清理")

            high_fragmentation_tables = [
                name for name, stats in table_stats.items()
                if stats.fragmentation_level > 0.3
            ]
            if high_fragmentation_tables:
                critical_issues.append(f"表{', '.join(high_fragmentation_tables)}碎片化严重")

            report = {
                "health_score": health_score,
                "summary": {
                    "tables_analyzed": len(table_stats),
                    "slow_queries": len(slow_queries),
                    "index_recommendations": sum(len(recs) for recs in index_recommendations.values()),
                    "pool_utilization": pool_optimization.get("current_pool_stats", {}).get("utilization_rate", 0)
                },
                "critical_issues": critical_issues,
                "detailed_analysis": {
                    "table_statistics": table_stats,
                    "index_recommendations": index_recommendations,
                    "slow_queries": [
                        {
                            "query_template": q.query_template,
                            "avg_duration": q.avg_duration,
                            "execution_count": q.execution_count,
                            "slow_count": q.slow_count
                        }
                        for q in slow_queries[:10]  # 只显示前10个
                    ],
                    "connection_pool": pool_optimization
                },
                "recommended_actions": self._generate_action_plan(
                    table_stats, index_recommendations, slow_queries, pool_optimization
                ),
                "timestamp": datetime.now().isoformat()
            }

            # 缓存报告
            await self.cache.set("database_optimization_report", report, ttl=600)

            logger.info("database_optimization_report_generated",
                        health_score=health_score,
                        critical_issues=len(critical_issues))

            return report

        except Exception as e:
            logger.error("database_optimization_report_failed", error=str(e))
            return {"error": str(e)}

    def _calculate_health_score(self, table_stats: Dict, index_recs: Dict,
                              slow_queries: List, pool_opt: Dict) -> float:
        """计算数据库健康评分"""
        score = 100.0

        # 慢查询影响
        if len(slow_queries) > 10:
            score -= 30
        elif len(slow_queries) > 5:
            score -= 15
        elif len(slow_queries) > 0:
            score -= 5

        # 表碎片化影响
        high_frag_count = sum(1 for stats in table_stats.values()
                            if stats.fragmentation_level > 0.3)
        if high_frag_count > 3:
            score -= 20
        elif high_frag_count > 1:
            score -= 10

        # 未使用索引影响
        unused_count = sum(len(recs) for recs in index_recs.values()
                         if any(r.index_type == "unused" for r in recs))
        if unused_count > 5:
            score -= 15
        elif unused_count > 2:
            score -= 8

        # 连接池优化评分
        pool_score = pool_opt.get("optimization_score", 100)
        score = score * (pool_score / 100)

        return max(score, 0)

    def _generate_action_plan(self, table_stats: Dict, index_recs: Dict,
                            slow_queries: List, pool_opt: Dict) -> List[Dict[str, str]]:
        """生成优化行动计划"""
        actions = []

        # 立即执行（高优先级）
        if slow_queries:
            actions.append({
                "priority": "high",
                "action": "优化慢查询",
                "details": f"发现{len(slow_queries)}个慢查询，需要分析执行计划并添加适当索引",
                "estimated_impact": "高"
            })

        # 短期执行（中优先级）
        high_frag_tables = [name for name, stats in table_stats.items()
                          if stats.fragmentation_level > 0.3]
        if high_frag_tables:
            actions.append({
                "priority": "medium",
                "action": "清理表碎片",
                "details": f"对表{', '.join(high_frag_tables)}执行VACUUM FULL",
                "estimated_impact": "中"
            })

        # 长期执行（低优先级）
        unused_indexes = []
        for table_name, recs in index_recs.items():
            for rec in recs:
                if rec.index_type == "unused":
                    unused_indexes.append(f"{table_name}.{rec.column_names[0]}")

        if unused_indexes:
            actions.append({
                "priority": "low",
                "action": "清理未使用索引",
                "details": f"删除索引：{', '.join(unused_indexes[:5])}",
                "estimated_impact": "低"
            })

        return actions

    async def cleanup_old_stats(self, days: int = 7):
        """清理旧的统计数据"""
        cutoff_date = datetime.now() - timedelta(days=days)

        # 清理查询统计
        old_queries = [
            hash_val for hash_val, stats in self._query_stats.items()
            if stats.last_executed < cutoff_date
        ]

        for hash_val in old_queries:
            del self._query_stats[hash_val]

        # 清理缓存中的统计数据
        await self.cache.delete("query_statistics")

        logger.info("old_stats_cleaned",
                   removed_queries=len(old_queries),
                   remaining_queries=len(self._query_stats))


async def init_database_optimization(config: dict) -> DatabaseOptimizer:
    """初始化数据库优化系统"""
    try:
        optimizer = DatabaseOptimizer()

        # 设置配置参数
        if 'slow_query_threshold' in config:
            optimizer._slow_query_threshold = config['slow_query_threshold']

        if 'max_stats_entries' in config:
            optimizer._max_stats_entries = config['max_stats_entries']

        # 启动时执行基础分析
        if config.get('enable_startup_analysis', False):
            await optimizer.analyze_table_usage()
            await optimizer.generate_index_recommendations()

        logger.info("database_optimization_initialized",
                   slow_query_threshold=optimizer._slow_query_threshold,
                   max_stats_entries=optimizer._max_stats_entries)

        return optimizer

    except Exception as e:
        logger.error("database_optimization_init_error", error=str(e))
        raise