"""
性能优化API端点

提供性能监控、优化建议、缓存管理等功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog

from ....core.auth import get_current_admin_user
from ....core.performance import (
    get_performance_status,
    CacheOptimizer,
    DatabaseOptimizer,
    ApiOptimizer
)
from ....core.cache.enhanced_cache import get_multi_cache
from ....core.database.optimized_pool import get_db_pool
from ....schemas.admin_operator import AdminOperatorResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="获取性能系统状态",
    description="获取缓存、数据库连接池、批处理管理器等组件的实时状态"
)
async def get_performance_status_endpoint(
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """获取性能系统状态"""
    try:
        status = get_performance_status()

        # 添加系统健康评分
        health_score = calculate_system_health_score(status)
        status["system_health_score"] = health_score
        status["timestamp"] = datetime.now().isoformat()

        return status

    except Exception as e:
        logger.error("get_performance_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/cache/stats",
    response_model=Dict[str, Any],
    summary="获取缓存统计信息",
    description="获取本地缓存和Redis缓存的详细统计信息"
)
async def get_cache_statistics(
    minutes: int = Query(60, ge=1, le=1440, description="统计时间范围（分钟）"),
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """获取缓存统计信息"""
    try:
        cache = get_multi_cache()
        stats = cache.get_stats()

        # 计算指定时间范围内的统计
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        # 获取缓存命中率趋势
        hit_rate_trend = await calculate_cache_hit_rate_trend(cache, minutes)

        return {
            "period_minutes": minutes,
            "current_stats": stats,
            "hit_rate_trend": hit_rate_trend,
            "recommendations": generate_cache_recommendations(stats),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error("get_cache_statistics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cache/warm",
    response_model=Dict[str, Any],
    summary="执行缓存预热",
    description="按策略执行缓存预热操作"
)
async def warm_cache(
    strategy: str = Query("all", description="预热策略名称"),
    max_concurrent: int = Query(10, ge=1, le=50, description="最大并发数"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """执行缓存预热"""
    try:
        # 异步执行预热任务
        background_tasks.add_task(execute_cache_warming, strategy, max_concurrent)

        return {
            "message": "缓存预热任务已启动",
            "strategy": strategy,
            "max_concurrent": max_concurrent,
            "estimated_duration": "2-5分钟",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error("warm_cache_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cache/invalidate",
    response_model=Dict[str, Any],
    summary="缓存失效",
    description="按键或模式失效缓存"
)
async def invalidate_cache(
    pattern: Optional[str] = Query(None, description="缓存模式"),
    keys: Optional[List[str]] = Query(None, description="缓存键列表"),
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """缓存失效"""
    try:
        if not pattern and not keys:
            raise HTTPException(status_code=400, detail="必须提供pattern或keys参数")

        cache = get_multi_cache()
        success_count = 0

        if pattern:
            await cache.invalidate_pattern(pattern)
            success_count = 1  # 模式失效无法统计具体数量
            logger.info("cache_invalidated_by_pattern", pattern=pattern)
        elif keys:
            for key in keys:
                if await cache.delete(key):
                    success_count += 1
            logger.info("cache_invalidated_by_keys", total_keys=len(keys), success_count=success_count)

        return {
            "message": "缓存失效操作完成",
            "invalidated_count": success_count,
            "pattern": pattern,
            "keys_count": len(keys) if keys else 0,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error("invalidate_cache_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/database/performance",
    response_model=Dict[str, Any],
    summary="获取数据库性能报告",
    description="获取数据库查询性能、索引建议、表统计等信息"
)
async def get_database_performance(
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """获取数据库性能报告"""
    try:
        # 这里需要实际的数据库优化器实例
        # 简化实现，返回模拟数据
        from ....core.performance.database_optimization import DatabaseOptimizer
        db_optimizer = DatabaseOptimizer()
        report = await db_optimizer.get_optimization_report()

        return report

    except Exception as e:
        logger.error("get_database_performance_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/database/slow-queries",
    response_model=List[Dict[str, Any]],
    summary="获取慢查询列表",
    description="获取指定时间范围内的慢查询"
)
async def get_slow_queries(
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
    min_count: int = Query(5, ge=1, le=100, description="最小执行次数"),
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> List[Dict[str, Any]]:
    """获取慢查询列表"""
    try:
        from ....core.performance.database_optimization import DatabaseOptimizer
        db_optimizer = DatabaseOptimizer()
        slow_queries = await db_optimizer.get_slow_queries(hours, min_count)

        return [
            {
                "query_template": q.query_template,
                "execution_count": q.execution_count,
                "avg_duration": q.avg_duration,
                "max_duration": q.max_duration,
                "slow_count": q.slow_count,
                "error_count": q.error_count,
                "last_executed": q.last_executed.isoformat()
            }
            for q in slow_queries
        ]

    except Exception as e:
        logger.error("get_slow_queries_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/statistics",
    response_model=Dict[str, Any],
    summary="获取API统计信息",
    description="获取API端点的性能统计和优化建议"
)
async def get_api_statistics(
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）"),
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """获取API统计信息"""
    try:
        from ....core.performance.api_optimization import ApiOptimizer
        api_optimizer = ApiOptimizer()
        statistics = await api_optimizer.get_endpoint_statistics(hours)

        return statistics

    except Exception as e:
        logger.error("get_api_statistics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/performance-report",
    response_model=Dict[str, Any],
    summary="获取API性能报告",
    description="获取综合API性能报告和优化建议"
)
async def get_api_performance_report(
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """获取API性能报告"""
    try:
        from ....core.performance.api_optimization import ApiOptimizer
        api_optimizer = ApiOptimizer()
        report = await api_optimizer.get_performance_report()

        return report

    except Exception as e:
        logger.error("get_api_performance_report_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/system/overview",
    response_model=Dict[str, Any],
    summary="系统性能概览",
    description="获取整个系统的性能概览和关键指标"
)
async def get_system_overview(
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """获取系统性能概览"""
    try:
        # 收集各组件状态
        performance_status = get_performance_status()

        # 获取缓存统计
        cache = get_multi_cache()
        cache_stats = cache.get_stats()

        # 获取数据库池状态
        db_pool = get_db_pool()
        pool_status = db_pool.get_pool_status()

        # 获取API统计
        from ....core.performance.api_optimization import ApiOptimizer
        api_optimizer = ApiOptimizer()
        api_stats = await api_optimizer.get_endpoint_statistics(1)  # 最近1小时

        # 计算关键指标
        overview = {
            "system_health": {
                "overall_score": calculate_system_health_score(performance_status),
                "cache_health": calculate_cache_health_score(cache_stats),
                "database_health": calculate_database_health_score(pool_status),
                "api_health": calculate_api_health_score(api_stats)
            },
            "key_metrics": {
                "cache_hit_rate": cache_stats.get("global", {}).get("hit_rate", 0),
                "database_pool_utilization": pool_status.get("utilization_rate", 0),
                "avg_response_time": api_stats.get("summary", {}).get("avg_response_time", 0),
                "success_rate": api_stats.get("summary", {}).get("success_rate", 0),
                "total_requests": api_stats.get("summary", {}).get("total_requests", 0)
            },
            "performance_alerts": generate_performance_alerts(
                performance_status, cache_stats, pool_status, api_stats
            ),
            "optimization_opportunities": generate_optimization_opportunities(
                performance_status, cache_stats, pool_status, api_stats
            ),
            "timestamp": datetime.now().isoformat()
        }

        return overview

    except Exception as e:
        logger.error("get_system_overview_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/optimize/recommendations",
    response_model=Dict[str, Any],
    summary="执行优化建议",
    description="根据分析结果执行系统优化操作"
)
async def execute_optimization_recommendations(
    background_tasks: BackgroundTasks,
    auto_execute: bool = Query(False, description="是否自动执行安全的优化操作"),
    current_user: AdminOperatorResponse = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """执行优化建议"""
    try:
        # 获取所有优化建议
        recommendations = await collect_all_recommendations()

        # 分类建议
        safe_recommendations = [r for r in recommendations if r.get("safe", False)]
        manual_recommendations = [r for r in recommendations if not r.get("safe", False)]

        executed = []
        if auto_execute and safe_recommendations:
            # 后台执行安全优化
            for rec in safe_recommendations:
                background_tasks.add_task(execute_safe_optimization, rec)
                executed.append(rec["title"])

        return {
            "message": "优化建议分析完成",
            "total_recommendations": len(recommendations),
            "safe_recommendations": len(safe_recommendations),
            "manual_recommendations": len(manual_recommendations),
            "auto_executed": executed if auto_execute else [],
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error("execute_optimization_recommendations_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# 辅助函数
def calculate_system_health_score(status: Dict[str, Any]) -> float:
    """计算系统健康评分"""
    scores = []

    # 缓存健康评分
    cache_stats = status.get("cache_system", {})
    if cache_stats.get("initialized") and cache_stats.get("stats"):
        hit_rate = cache_stats["stats"].get("global", {}).get("hit_rate", 0)
        scores.append(hit_rate * 100)
    else:
        scores.append(0)

    # 数据库健康评分
    pool_stats = status.get("database_pool", {})
    if pool_stats.get("initialized"):
        utilization = pool_stats.get("status", {}).get("utilization_rate", 0)
        # 利用率在70%以下为健康
        scores.append(max(0, 100 - (utilization - 0.7) * 500))
    else:
        scores.append(0)

    # 批处理管理器健康评分
    batch_stats = status.get("batch_manager", {})
    if batch_stats.get("initialized"):
        scores.append(100)  # 批处理管理器通常比较稳定
    else:
        scores.append(0)

    return sum(scores) / len(scores) if scores else 0


async def calculate_cache_hit_rate_trend(cache, minutes: int) -> List[Dict[str, float]]:
    """计算缓存命中率趋势"""
    # 简化实现，返回模拟数据
    # 实际应该从时序数据库或监控系统获取历史数据
    import random

    trend = []
    now = datetime.now()
    for i in range(minutes // 5):  # 每5分钟一个数据点
        timestamp = now - timedelta(minutes=(i + 1) * 5)
        hit_rate = 0.7 + random.random() * 0.2  # 70%-90%
        trend.append({
            "timestamp": timestamp.isoformat(),
            "hit_rate": hit_rate
        })

    return list(reversed(trend))


def generate_cache_recommendations(stats: Dict[str, Any]) -> List[str]:
    """生成缓存优化建议"""
    recommendations = []

    hit_rate = stats.get("global", {}).get("hit_rate", 0)
    if hit_rate < 0.5:
        recommendations.append("缓存命中率较低，建议检查缓存策略和TTL设置")

    local_stats = stats.get("local_cache", {}).get("stats", {})
    if local_stats.get("hit_rate", 0) < 0.4:
        recommendations.append("本地缓存命中率较低，建议增加本地缓存大小")

    size_info = stats.get("local_cache", {}).get("size_info", {})
    if size_info.get("utilization_rate", 0) > 0.9:
        recommendations.append("本地缓存利用率过高，建议增加缓存容量")

    return recommendations


def calculate_cache_health_score(stats: Dict[str, Any]) -> float:
    """计算缓存健康评分"""
    hit_rate = stats.get("global", {}).get("hit_rate", 0)
    return hit_rate * 100


def calculate_database_health_score(pool_status: Dict[str, Any]) -> float:
    """计算数据库健康评分"""
    utilization = pool_status.get("utilization_rate", 0)
    wait_count = pool_status.get("wait_count", 0)

    score = 100
    if utilization > 0.8:
        score -= 30
    elif utilization > 0.6:
        score -= 15

    if wait_count > 0:
        score -= 20

    return max(score, 0)


def calculate_api_health_score(api_stats: Dict[str, Any]) -> float:
    """计算API健康评分"""
    summary = api_stats.get("summary", {})

    success_rate = summary.get("success_rate", 1.0)
    avg_response_time = summary.get("avg_response_time", 0)

    score = success_rate * 80  # 成功率权重80%

    # 响应时间评分
    if avg_response_time < 0.5:
        score += 20
    elif avg_response_time < 1.0:
        score += 15
    elif avg_response_time < 2.0:
        score += 5

    return min(score, 100)


def generate_performance_alerts(status, cache_stats, pool_status, api_stats) -> List[Dict[str, Any]]:
    """生成性能告警"""
    alerts = []

    # 缓存告警
    hit_rate = cache_stats.get("global", {}).get("hit_rate", 0)
    if hit_rate < 0.5:
        alerts.append({
            "type": "cache",
            "severity": "warning",
            "title": "缓存命中率过低",
            "description": f"当前缓存命中率为{hit_rate:.1%}，低于健康阈值"
        })

    # 数据库告警
    utilization = pool_status.get("utilization_rate", 0)
    if utilization > 0.8:
        alerts.append({
            "type": "database",
            "severity": "critical",
            "title": "数据库连接池利用率过高",
            "description": f"当前连接池利用率为{utilization:.1%}，可能影响性能"
        })

    # API告警
    success_rate = api_stats.get("summary", {}).get("success_rate", 1.0)
    if success_rate < 0.95:
        alerts.append({
            "type": "api",
            "severity": "warning",
            "title": "API成功率下降",
            "description": f"当前API成功率为{success_rate:.1%}，低于正常水平"
        })

    return alerts


def generate_optimization_opportunities(status, cache_stats, pool_status, api_stats) -> List[Dict[str, Any]]:
    """生成优化机会"""
    opportunities = []

    # 缓存优化
    hit_rate = cache_stats.get("global", {}).get("hit_rate", 0)
    if hit_rate < 0.7:
        opportunities.append({
            "type": "cache",
            "title": "优化缓存策略",
            "description": "提高缓存命中率可以显著改善性能",
            "potential_impact": "high",
            "effort": "medium"
        })

    # API优化
    avg_response_time = api_stats.get("summary", {}).get("avg_response_time", 0)
    if avg_response_time > 1.0:
        opportunities.append({
            "type": "api",
            "title": "优化API响应时间",
            "description": "通过缓存和查询优化减少响应时间",
            "potential_impact": "high",
            "effort": "medium"
        })

    return opportunities


async def execute_cache_warming(strategy: str, max_concurrent: int):
    """执行缓存预热"""
    try:
        from ....core.performance.cache_optimization import CacheOptimizer
        optimizer = CacheOptimizer()

        if strategy == "all":
            await optimizer.warm_all_cache(max_concurrent)
        else:
            await optimizer.warm_cache(strategy, max_concurrent)

        logger.info("cache_warming_completed", strategy=strategy)
    except Exception as e:
        logger.error("cache_warming_failed", strategy=strategy, error=str(e))


async def collect_all_recommendations() -> List[Dict[str, Any]]:
    """收集所有优化建议"""
    recommendations = []

    # 缓存建议
    cache = get_multi_cache()
    cache_stats = cache.get_stats()
    cache_recs = generate_cache_recommendations(cache_stats)
    for rec in cache_recs:
        recommendations.append({
            "category": "cache",
            "title": rec,
            "safe": False,
            "priority": "medium"
        })

    # 数据库建议
    db_pool = get_db_pool()
    pool_status = db_pool.get_pool_status()
    if pool_status.get("utilization_rate", 0) > 0.8:
        recommendations.append({
            "category": "database",
            "title": "增加数据库连接池大小",
            "safe": False,
            "priority": "high"
        })

    return recommendations


async def execute_safe_optimization(recommendation: Dict[str, Any]):
    """执行安全的优化操作"""
    try:
        # 这里实现具体的安全优化操作
        logger.info("executing_safe_optimization", recommendation=recommendation["title"])
        # 实际实现...
    except Exception as e:
        logger.error("safe_optimization_failed", recommendation=recommendation["title"], error=str(e))