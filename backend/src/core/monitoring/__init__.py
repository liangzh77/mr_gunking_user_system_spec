"""
监控系统初始化模块

提供监控系统的统一初始化接口
"""
import structlog
from .health_monitor import initialize_health_monitoring, health_monitor
from .alert_system import initialize_alert_system, alert_manager
from ..metrics.enhanced_metrics import metrics_collector
from ..metrics.prometheus import setup_prometheus_metrics

logger = structlog.get_logger(__name__)


async def initialize_monitoring_system(app, config: dict):
    """
    初始化完整的监控系统

    Args:
        app: FastAPI应用实例
        config: 监控配置
    """
    try:
        logger.info("initializing_monitoring_system")

        # 1. 设置Prometheus指标
        setup_prometheus_metrics(app)
        logger.info("prometheus_metrics_configured")

        # 2. 启动增强指标收集
        await metrics_collector.start_collection()
        logger.info("enhanced_metrics_collection_started")

        # 3. 初始化健康监控
        await initialize_health_monitoring(config.get('health_monitoring', {}))
        logger.info("health_monitoring_initialized")

        # 4. 初始化告警系统
        await initialize_alert_system(config.get('alert_system', {}))
        logger.info("alert_system_initialized")

        # 5. 设置应用关闭时的清理工作
        @app.on_event("shutdown")
        async def cleanup_monitoring():
            logger.info("cleaning_up_monitoring_system")
            await metrics_collector.stop_collection()
            await health_monitor.stop_monitoring()
            await alert_manager.stop_monitoring()
            logger.info("monitoring_system_cleanup_completed")

        logger.info("monitoring_system_initialization_completed",
                   health_checks=len(health_monitor.checks),
                   alert_rules=len(alert_manager.rule_engine.rules),
                   notification_channels=len(alert_manager.notification_channels))

    except Exception as e:
        logger.error("monitoring_system_initialization_failed", error=str(e))
        raise


def get_monitoring_status() -> dict:
    """
    获取监控系统状态

    Returns:
        监控系统状态信息
    """
    try:
        return {
            "enhanced_metrics": {
                "collecting": metrics_collector.is_collecting,
                "collection_interval": metrics_collector.collection_interval,
                "metrics_count": len(metrics_collector.registry._collector_to_names)
            },
            "health_monitoring": {
                "monitoring_active": health_monitor.is_running,
                "check_interval": health_monitor.check_interval,
                "total_checks": len(health_monitor.checks),
                "last_check_results": len(health_monitor.last_check_results)
            },
            "alert_system": {
                "monitoring_active": alert_manager.is_running,
                "evaluation_interval": alert_manager.evaluation_interval,
                "total_alerts": len(alert_manager.alerts),
                "active_alerts": len(alert_manager.get_active_alerts()),
                "total_rules": len(alert_manager.rule_engine.rules),
                "notification_channels": len(alert_manager.notification_channels)
            }
        }
    except Exception as e:
        logger.error("get_monitoring_status_error", error=str(e))
        return {"error": str(e)}


# 导出主要组件
__all__ = [
    'initialize_monitoring_system',
    'get_monitoring_status',
    'health_monitor',
    'alert_manager',
    'metrics_collector'
]