"""
监控API端点

提供全面的监控数据访问接口，包括实时指标、健康状态、性能数据等
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog

from ...core.monitoring.health_monitor import (
    health_monitor,
    CheckLevel,
    get_health_summary
)
from ...core.metrics.enhanced_metrics import (
    metrics_collector,
    get_metrics_summary
)
from ...core.metrics.prometheus import generate_latest, REGISTRY
from ...auth.dependencies import get_admin_token

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/health", summary="获取系统健康状态")
async def get_system_health(
    level: CheckLevel = Query(CheckLevel.STANDARD, description="检查级别"),
    admin_token: str = Depends(get_admin_token)
) -> Dict[str, Any]:
    """
    获取系统健康状态

    Args:
        level: 检查级别 (basic/standard/comprehensive)
        admin_token: 管理员认证令牌

    Returns:
        系统健康状态摘要
    """
    try:
        # 执行健康检查
        health_summary = await health_monitor.run_checks(level)

        return {
            "success": True,
            "data": {
                "overall_status": health_summary.overall_status.value,
                "timestamp": health_summary.timestamp.isoformat(),
                "total_checks": health_summary.total_checks,
                "passed_checks": health_summary.passed_checks,
                "failed_checks": health_summary.failed_checks,
                "service_uptime_seconds": health_summary.service_uptime,
                "performance_metrics": health_summary.performance_metrics,
                "checks": [
                    {
                        "component": result.component,
                        "type": result.check_type,
                        "status": result.status.value,
                        "message": result.message,
                        "duration_ms": result.duration_ms,
                        "timestamp": result.timestamp.isoformat(),
                        "details": result.details,
                        "threshold_exceeded": result.threshold_exceeded
                    }
                    for result in health_summary.check_results
                ]
            }
        }
    except Exception as e:
        logger.error("get_health_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取健康状态失败: {str(e)}")


@router.get("/health/summary", summary="获取健康状态摘要")
async def get_health_summary_endpoint(
    admin_token: str = Depends(get_admin_token)
) -> Dict[str, Any]:
    """
    获取健康状态摘要（不执行新的检查）

    Returns:
        最新的健康状态摘要
    """
    try:
        summary = health_monitor.get_health_summary()
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        logger.error("get_health_summary_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取健康摘要失败: {str(e)}")


@router.get("/health/trends", summary="获取健康趋势")
async def get_health_trends(
    hours: int = Query(24, ge=1, le=168, description="查询时间范围（小时）"),
    admin_token: str = Depends(get_admin_token)
) -> Dict[str, Any]:
    """
    获取健康趋势数据

    Args:
        hours: 查询时间范围（1-168小时）
        admin_token: 管理员认证令牌

    Returns:
        健康趋势数据
    """
    try:
        trends = health_monitor.get_health_trends(hours)
        return {
            "success": True,
            "data": trends
        }
    except Exception as e:
        logger.error("get_health_trends_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取健康趋势失败: {str(e)}")


@router.get("/metrics", summary="获取Prometheus指标")
async def get_prometheus_metrics(
    admin_token: str = Depends(get_admin_token)
) -> JSONResponse:
    """
    获取Prometheus格式的监控指标

    Returns:
        Prometheus格式的指标数据
    """
    try:
        metrics_data = generate_latest(REGISTRY)
        return JSONResponse(
            content=metrics_data.decode('utf-8'),
            media_type="text/plain; version=0.0.4"
        )
    except Exception as e:
        logger.error("get_metrics_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取指标失败: {str(e)}")


@router.get("/metrics/summary", summary="获取指标摘要")
async def get_metrics_summary_endpoint(
    admin_token: str = Depends(get_admin_token)
) -> Dict[str, Any]:
    """
    获取指标收集摘要信息

    Returns:
        指标收集状态和统计信息
    """
    try:
        summary = get_metrics_summary()
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        logger.error("get_metrics_summary_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取指标摘要失败: {str(e)}")


@router.get("/dashboard", summary="获取监控仪表板数据")
async def get_dashboard_data(
    admin_token: str = Depends(get_admin_token)
) -> Dict[str, Any]:
    """
    获取监控仪表板数据（综合视图）

    Returns:
        包含健康状态、性能指标、趋势等的综合数据
    """
    try:
        # 获取健康状态
        health_summary = health_monitor.get_health_summary()

        # 获取指标摘要
        metrics_summary = get_metrics_summary()

        # 获取健康趋势
        health_trends = health_monitor.get_health_trends(24)

        # 获取业务指标（模拟数据，实际应从数据库或缓存获取）
        business_metrics = await get_business_metrics()

        return {
            "success": True,
            "data": {
                "health": health_summary,
                "metrics": metrics_summary,
                "trends": health_trends,
                "business": business_metrics,
                "alerts": await get_active_alerts(),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error("get_dashboard_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取仪表板数据失败: {str(e)}")


@router.get("/alerts", summary="获取活跃告警")
async def get_active_alerts_endpoint(
    severity: Optional[str] = Query(None, description="告警严重级别过滤"),
    admin_token: str = Depends(get_admin_token)
) -> Dict[str, Any]:
    """
    获取活跃告警列表

    Args:
        severity: 告警严重级别过滤 (critical/warning/info)
        admin_token: 管理员认证令牌

    Returns:
        活跃告警列表
    """
    try:
        alerts = await get_active_alerts(severity)
        return {
            "success": True,
            "data": {
                "alerts": alerts,
                "total_count": len(alerts),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error("get_alerts_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取告警失败: {str(e)}")


@router.get("/performance", summary="获取性能指标")
async def get_performance_metrics(
    period: str = Query("1h", description="时间周期 (1h/6h/24h/7d)"),
    admin_token: str = Depends(get_admin_token)
) -> Dict[str, Any]:
    """
    获取性能指标

    Args:
        period: 时间周期
        admin_token: 管理员认证令牌

    Returns:
        性能指标数据
    """
    try:
        performance_data = await get_performance_data(period)
        return {
            "success": True,
            "data": performance_data
        }
    except Exception as e:
        logger.error("get_performance_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")


@router.post("/checks/run", summary="手动执行健康检查")
async def run_health_checks(
    level: CheckLevel = Query(CheckLevel.STANDARD, description="检查级别"),
    admin_token: str = Depends(get_admin_token)
) -> Dict[str, Any]:
    """
    手动执行健康检查

    Args:
        level: 检查级别
        admin_token: 管理员认证令牌

    Returns:
        检查结果
    """
    try:
        # 执行健康检查
        health_summary = await health_monitor.run_checks(level)

        logger.info("manual_health_checks_executed",
                   level=level.value,
                   total_checks=health_summary.total_checks,
                   passed_checks=health_summary.passed_checks,
                   failed_checks=health_summary.failed_checks)

        return {
            "success": True,
            "message": f"健康检查执行完成，级别: {level.value}",
            "data": {
                "overall_status": health_summary.overall_status.value,
                "timestamp": health_summary.timestamp.isoformat(),
                "total_checks": health_summary.total_checks,
                "passed_checks": health_summary.passed_checks,
                "failed_checks": health_summary.failed_checks,
                "execution_time_seconds": health_summary.performance_metrics.get('avg_check_duration_ms', 0) / 1000
            }
        }
    except Exception as e:
        logger.error("run_health_checks_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"执行健康检查失败: {str(e)}")


@router.get("/components", summary="获取监控组件状态")
async def get_monitoring_components(
    admin_token: str = Depends(get_admin_token)
) -> Dict[str, Any]:
    """
    获取监控组件状态

    Returns:
        监控组件列表和状态
    """
    try:
        components = []

        # 健康监控器状态
        components.append({
            "name": "health_monitor",
            "type": "monitoring",
            "status": "running" if health_monitor.is_running else "stopped",
            "last_check": health_monitor.get_health_summary().get("timestamp"),
            "checks_count": len(health_monitor.checks),
            "interval_seconds": health_monitor.check_interval
        })

        # 指标收集器状态
        components.append({
            "name": "metrics_collector",
            "type": "metrics",
            "status": "running" if metrics_collector.is_collecting else "stopped",
            "collection_interval": metrics_collector.collection_interval,
            "metrics_count": len(REGISTRY._collector_to_names)
        })

        # 各个健康检查组件状态
        for check_name, check in health_monitor.checks.items():
            components.append({
                "name": check_name,
                "type": "health_check",
                "status": "active",
                "last_check": check.last_check_time.isoformat() if check.last_check_time else None,
                "consecutive_failures": check.consecutive_failures,
                "timeout_seconds": check.timeout
            })

        return {
            "success": True,
            "data": {
                "components": components,
                "total_count": len(components),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error("get_components_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取组件状态失败: {str(e)}")


# ========== 辅助函数 ==========

async def get_business_metrics() -> Dict[str, Any]:
    """
    获取业务指标

    Returns:
        业务指标数据
    """
    # 这里应该从实际的业务数据库或缓存获取数据
    # 目前返回模拟数据
    return {
        "active_sessions": 156,
        "total_players": 624,
        "revenue_today": 12580.50,
        "revenue_month": 387650.00,
        "active_operators": 45,
        "total_transactions_today": 1240,
        "avg_session_duration_minutes": 45.5,
        "conversion_rate": 0.085,
        "top_games": [
            {"name": "Game A", "sessions": 89, "revenue": 5234.00},
            {"name": "Game B", "sessions": 67, "revenue": 3890.50},
            {"name": "Game C", "sessions": 45, "revenue": 2156.00}
        ],
        "recent_alerts_count": 3
    }


async def get_active_alerts(severity: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取活跃告警

    Args:
        severity: 告警严重级别过滤

    Returns:
        活跃告警列表
    """
    # 这里应该从实际的告警系统获取数据
    # 目前返回模拟数据
    all_alerts = [
        {
            "id": "alert_001",
            "title": "数据库连接池使用率过高",
            "description": "数据库连接池使用率达到85%，超过阈值",
            "severity": "warning",
            "status": "active",
            "component": "database",
            "created_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "threshold_exceeded": "connection_pool_usage > 80%"
        },
        {
            "id": "alert_002",
            "title": "Redis内存使用率偏高",
            "description": "Redis内存使用率达到78%，接近警告阈值",
            "severity": "info",
            "status": "active",
            "component": "redis",
            "created_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "threshold_exceeded": "memory_usage > 75%"
        },
        {
            "id": "alert_003",
            "title": "API响应时间异常",
            "description": "/v1/games/authorize接口平均响应时间超过500ms",
            "severity": "critical",
            "status": "active",
            "component": "api",
            "created_at": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "threshold_exceeded": "response_time > 500ms"
        }
    ]

    # 根据严重级别过滤
    if severity:
        all_alerts = [alert for alert in all_alerts if alert["severity"] == severity]

    return all_alerts


async def get_performance_data(period: str) -> Dict[str, Any]:
    """
    获取性能数据

    Args:
        period: 时间周期

    Returns:
        性能数据
    """
    # 解析时间周期
    period_mapping = {
        "1h": 1,
        "6h": 6,
        "24h": 24,
        "7d": 168
    }

    hours = period_mapping.get(period, 1)

    # 这里应该从实际的监控系统获取数据
    # 目前返回模拟数据
    import random

    # 生成时间序列数据
    time_points = []
    now = datetime.now()

    for i in range(hours):
        point_time = now - timedelta(hours=i)
        time_points.append({
            "timestamp": point_time.isoformat(),
            "cpu_usage": random.uniform(20, 80),
            "memory_usage": random.uniform(30, 70),
            "response_time": random.uniform(50, 300),
            "request_rate": random.uniform(10, 100),
            "error_rate": random.uniform(0, 5)
        })

    return {
        "period": period,
        "hours": hours,
        "time_series": list(reversed(time_points)),
        "summary": {
            "avg_cpu_usage": random.uniform(30, 60),
            "avg_memory_usage": random.uniform(40, 65),
            "avg_response_time": random.uniform(100, 200),
            "total_requests": random.randint(1000, 10000),
            "error_rate": random.uniform(0.1, 2.0)
        }
    }