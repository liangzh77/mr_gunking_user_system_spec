"""
缓存优化模块

提供缓存预热、缓存失效、缓存策略优化等功能
"""
import asyncio
import time
import structlog
from typing import Any, Dict, List, Optional, Callable, TypeVar
from datetime import datetime, timedelta

from ..cache.enhanced_cache import (
    get_multi_cache,
    get_cache_warmer,
    CacheLevel
)

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class CacheOptimizer:
    """缓存优化器"""

    def __init__(self):
        self.cache = get_multi_cache()
        self.cache_warmer = get_cache_warmer()
        self._warming_strategies = {}
        self._invalidation_rules = {}
        self._performance_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'invalidations': 0
        }

    def register_warming_strategy(self, name: str, warmers: Dict[str, Callable]):
        """注册缓存预热策略"""
        self._warming_strategies[name] = warmers
        logger.info("warming_strategy_registered", name=name, warmers_count=len(warmers))

    def register_invalidation_rule(self, pattern: str, handler: Callable):
        """注册缓存失效规则"""
        self._invalidation_rules[pattern] = handler
        logger.info("invalidation_rule_registered", pattern=pattern)

    async def warm_cache(self, strategy_name: str, max_concurrent: int = 10):
        """执行缓存预热"""
        if strategy_name not in self._warming_strategies:
            logger.error("warming_strategy_not_found", strategy_name=strategy_name)
            return

        warmers = self._warming_strategies[strategy_name]
        await self.cache_warmer.warm_cache(warmers, max_concurrent)

        logger.info("cache_warming_completed", strategy_name=strategy_name)

    async def warm_all_cache(self, max_concurrent: int = 10):
        """执行所有缓存预热策略"""
        all_warmers = {}
        for strategy_name, warmers in self._warming_strategies.items():
            all_warmers.update(warmers)

        await self.cache_warmer.warm_cache(all_warmers, max_concurrent)
        logger.info("all_cache_warming_completed", total_warmers=len(all_warmers))

    async def invalidate_by_pattern(self, pattern: str):
        """按模式失效缓存"""
        try:
            await self.cache.invalidate_pattern(pattern)

            # 执行注册的失效规则
            if pattern in self._invalidation_rules:
                await self._invalidation_rules[pattern]()

            self._performance_stats['invalidations'] += 1
            logger.info("cache_invalidated_by_pattern", pattern=pattern)

        except Exception as e:
            logger.error("cache_invalidation_error", pattern=pattern, error=str(e))

    async def invalidate_by_keys(self, keys: List[str], use_redis: bool = True):
        """按键失效缓存"""
        success_count = 0
        for key in keys:
            if await self.cache.delete(key, use_redis=use_redis):
                success_count += 1

        self._performance_stats['invalidations'] += success_count
        logger.info("cache_invalidated_by_keys", total_keys=len(keys), success_count=success_count)

    async def get_cache_hit_rate(self, minutes: int = 60) -> Dict[str, Any]:
        """获取缓存命中率"""
        stats = self.cache.get_stats()
        hit_rate = stats['global']['hit_rate']

        return {
            'period_minutes': minutes,
            'global_hit_rate': hit_rate,
            'local_cache': {
                'hit_rate': stats['local_cache']['stats']['hit_rate'],
                'hits': stats['local_cache']['stats']['hits'],
                'misses': stats['local_cache']['stats']['misses']
            },
            'redis_cache': {
                'hit_rate': stats['redis_cache']['stats']['hit_rate'] if stats['redis_cache']['stats'] else 0,
                'hits': stats['redis_cache']['stats']['hits'] if stats['redis_cache']['stats'] else 0,
                'misses': stats['redis_cache']['stats']['misses'] if stats['redis_cache']['stats'] else 0
            }
        }

    async def get_cache_performance_report(self) -> Dict[str, Any]:
        """获取缓存性能报告"""
        stats = self.cache.get_stats()
        recommendations = []

        # 分析命中率
        global_hit_rate = stats['global']['hit_rate']
        if global_hit_rate < 0.7:
            recommendations.append(
                f"全局缓存命中率较低({global_hit_rate:.2%})，建议检查缓存策略或增加缓存时间"
            )

        # 分析本地缓存
        local_stats = stats['local_cache']['stats']
        if local_stats['hit_rate'] < 0.6:
            recommendations.append(
                f"本地缓存命中率较低({local_stats['hit_rate']:.2%})，建议增加本地缓存大小"
            )

        # 分析利用率
        local_size_info = stats['local_cache']['size_info']
        if local_size_info['utilization_rate'] > 0.9:
            recommendations.append(
                f"本地缓存利用率过高({local_size_info['utilization_rate']:.2%})，建议增加缓存大小"
            )

        return {
            'performance_stats': stats,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }

    def update_performance_stats(self, operation: str, cache_type: str, result: str):
        """更新性能统计"""
        if operation == 'hit':
            self._performance_stats['hits'] += 1
        elif operation == 'miss':
            self._performance_stats['misses'] += 1
        elif operation == 'set':
            self._performance_stats['sets'] += 1


# 预定义的预热策略
class PredefinedWarmingStrategies:
    """预定义的缓存预热策略"""

    @staticmethod
    def get_operator_warmers() -> Dict[str, Callable]:
        """运营商数据预热策略"""
        async def warm_operators():
            # 这里应该从数据库获取运营商数据
            # 返回模拟数据用于演示
            return [
                {"operator_id": "1", "username": "operator1", "balance": 1000},
                {"operator_id": "2", "username": "operator2", "balance": 2000}
            ]

        async def warm_operator_balance():
            # 预热运营商余额数据
            return [
                {"operator_id": "1", "balance": 1000, "available_balance": 950},
                {"operator_id": "2", "balance": 2000, "available_balance": 1950}
            ]

        return {
            'operators': warm_operators,
            'operator_balances': warm_operator_balance
        }

    @staticmethod
    def get_game_warmers() -> Dict[str, Callable]:
        """游戏数据预热策略"""
        async def warm_game_apps():
            # 预热游戏应用数据
            return [
                {"app_id": 1, "app_name": "Game A", "cost_per_minute": 0.5},
                {"app_id": 2, "app_name": "Game B", "cost_per_minute": 0.3}
            ]

        async def warm_game_sessions():
            # 预热活跃游戏会话数据
            return [
                {"session_id": "session1", "app_id": 1, "player_count": 4},
                {"session_id": "session2", "app_id": 2, "player_count": 2}
            ]

        return {
            'game_apps': warm_game_apps,
            'game_sessions': warm_game_sessions
        }

    @staticmethod
    def get_statistics_warmers() -> Dict[str, Callable]:
        """统计数据预热策略"""
        async def warm_consumption_stats():
            # 预热消费统计数据
            return {
                "total_players": 100,
                "total_sessions": 50,
                "total_cost": 500.0,
                "period": "last_24h"
            }

        async def warm_revenue_stats():
            # 预热收入统计数据
            return {
                "daily_revenue": 10000.0,
                "weekly_revenue": 50000.0,
                "growth_rate": 0.15
            }

        return {
            'consumption_stats': warm_consumption_stats,
            'revenue_stats': warm_revenue_stats
        }


async def init_cache_optimization(config: dict) -> CacheOptimizer:
    """初始化缓存优化系统"""
    try:
        optimizer = CacheOptimizer()

        # 注册预定义的预热策略
        optimizer.register_warming_strategy('operators', PredefinedWarmingStrategies.get_operator_warmers())
        optimizer.register_warming_strategy('games', PredefinedWarmingStrategies.get_game_warmers())
        optimizer.register_warming_strategy('statistics', PredefinedWarmingStrategies.get_statistics_warmers())

        # 注册失效规则
        def operator_invalidation(pattern: str):
            # 运营商数据失效规则
            pass

        def game_session_invalidation(pattern: str):
            # 游戏会话数据失效规则
            pass

        optimizer.register_invalidation_rule("operator:*", operator_invalidation)
        optimizer.register_invalidation_rule("session:*", game_session_invalidation)

        # 自动预热（如果配置启用）
        if config.get('auto_warmup', False):
            await optimizer.warm_all_cache(
                max_concurrent=config.get('max_concurrent_warmers', 5)
            )

        logger.info("cache_optimization_initialized")
        return optimizer

    except Exception as e:
        logger.error("cache_optimization_init_error", error=str(e))
        raise