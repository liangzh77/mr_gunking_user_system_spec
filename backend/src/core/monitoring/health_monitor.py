"""
健康监控和检查系统

提供全面的服务健康检查、监控指标收集和预警功能
"""
import asyncio
import time
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import asyncpg
import redis.asyncio as redis
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

from ..metrics.enhanced_metrics import (
    record_health_check,
    metrics_collector,
    service_availability,
    error_rate,
    sla_compliance
)

logger = structlog.get_logger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckLevel(Enum):
    """检查级别"""
    BASIC = "basic"      # 基础检查
    STANDARD = "standard"  # 标准检查
    COMPREHENSIVE = "comprehensive"  # 全面检查


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component: str
    check_type: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    threshold_exceeded: Optional[str] = None


@dataclass
class SystemHealthSummary:
    """系统健康摘要"""
    overall_status: HealthStatus
    timestamp: datetime
    total_checks: int
    passed_checks: int
    failed_checks: int
    check_results: List[HealthCheckResult]
    service_uptime: float
    performance_metrics: Dict[str, float]


class HealthCheck:
    """健康检查基类"""

    def __init__(self, name: str, timeout: float = 10.0):
        self.name = name
        self.timeout = timeout
        self.last_check_time: Optional[datetime] = None
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3

    async def check(self) -> HealthCheckResult:
        """执行健康检查"""
        start_time = time.time()
        timestamp = datetime.now()

        try:
            # 执行具体检查逻辑
            result = await self.execute_check()

            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000

            # 创建检查结果
            health_result = HealthCheckResult(
                component=self.name,
                check_type=self.__class__.__name__.lower().replace('check', ''),
                status=result.status,
                message=result.message,
                duration_ms=duration_ms,
                timestamp=timestamp,
                details=result.details,
                threshold_exceeded=result.threshold_exceeded
            )

            # 更新检查状态
            self._update_check_status(health_result.status)

            # 记录指标
            record_health_check(
                component=self.name,
                check_type=health_result.check_type,
                success=health_result.status == HealthStatus.HEALTHY,
                duration=duration_ms / 1000
            )

            return health_result

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                component=self.name,
                check_type=self.__class__.__name__.lower().replace('check', ''),
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timeout after {self.timeout}s",
                duration_ms=duration_ms,
                timestamp=timestamp,
                threshold_exceeded="timeout"
            )

            self._update_check_status(result.status)
            record_health_check(self.name, result.check_type, False, duration_ms / 1000)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                component=self.name,
                check_type=self.__class__.__name__.lower().replace('check', ''),
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=timestamp
            )

            self._update_check_status(result.status)
            record_health_check(self.name, result.check_type, False, duration_ms / 1000)
            logger.error("health_check_error", component=self.name, error=str(e))
            return result

    async def execute_check(self) -> HealthCheckResult:
        """子类需要实现的具体检查逻辑"""
        raise NotImplementedError

    def _update_check_status(self, status: HealthStatus):
        """更新检查状态"""
        self.last_check_time = datetime.now()

        if status == HealthStatus.HEALTHY:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1


class DatabaseHealthCheck(HealthCheck):
    """数据库健康检查"""

    def __init__(self, db_url: str, **kwargs):
        super().__init__("database", **kwargs)
        self.db_url = db_url

    async def execute_check(self) -> HealthCheckResult:
        try:
            # 测试数据库连接
            engine = create_async_engine(self.db_url)

            async with engine.begin() as conn:
                # 执行简单查询
                result = await conn.execute(text("SELECT 1 as health_check"))
                row = result.first()

                if row and row.health_check == 1:
                    # 获取连接池信息
                    pool = engine.pool
                    details = {
                        'pool_size': pool.size(),
                        'checked_in': pool.checkedin(),
                        'checked_out': pool.checkedout(),
                        'overflow': pool.overflow()
                    }

                    await engine.dispose()

                    return HealthCheckResult(
                        component=self.name,
                        check_type="database",
                        status=HealthStatus.HEALTHY,
                        message="Database connection successful",
                        duration_ms=0,  # 将在父类中设置
                        timestamp=datetime.now(),
                        details=details
                    )
                else:
                    return HealthCheckResult(
                        component=self.name,
                        check_type="database",
                        status=HealthStatus.UNHEALTHY,
                        message="Database query returned unexpected result",
                        duration_ms=0,
                        timestamp=datetime.now()
                    )

        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                check_type="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                duration_ms=0,
                timestamp=datetime.now()
            )


class RedisHealthCheck(HealthCheck):
    """Redis健康检查"""

    def __init__(self, redis_url: str, **kwargs):
        super().__init__("redis", **kwargs)
        self.redis_url = redis_url

    async def execute_check(self) -> HealthCheckResult:
        try:
            # 连接Redis
            redis_client = redis.from_url(self.redis_url)

            # 执行ping命令
            start_time = time.time()
            pong = await redis_client.ping()
            ping_duration = (time.time() - start_time) * 1000

            # 获取Redis信息
            info = await redis_client.info()
            await redis_client.close()

            if pong:
                details = {
                    'ping_duration_ms': ping_duration,
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory', 0),
                    'uptime_seconds': info.get('uptime_in_seconds', 0)
                }

                # 检查延迟阈值
                threshold_exceeded = None
                if ping_duration > 100:  # 100ms阈值
                    threshold_exceeded = f"High latency: {ping_duration:.2f}ms"

                status = HealthStatus.HEALTHY
                if threshold_exceeded:
                    status = HealthStatus.DEGRADED

                return HealthCheckResult(
                    component=self.name,
                    check_type="redis",
                    status=status,
                    message="Redis connection successful",
                    duration_ms=0,
                    timestamp=datetime.now(),
                    details=details,
                    threshold_exceeded=threshold_exceeded
                )
            else:
                return HealthCheckResult(
                    component=self.name,
                    check_type="redis",
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping failed",
                    duration_ms=0,
                    timestamp=datetime.now()
                )

        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                check_type="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                duration_ms=0,
                timestamp=datetime.now()
            )


class ExternalAPIHealthCheck(HealthCheck):
    """外部API健康检查"""

    def __init__(self, api_name: str, api_url: str, **kwargs):
        super().__init__(api_name, **kwargs)
        self.api_url = api_url

    async def execute_check(self) -> HealthCheckResult:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start_time = time.time()
                response = await client.get(self.api_url)
                duration = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    details = {
                        'status_code': response.status_code,
                        'response_duration_ms': duration,
                        'response_size': len(response.content)
                    }

                    # 检查性能阈值
                    threshold_exceeded = None
                    if duration > 1000:  # 1秒阈值
                        threshold_exceeded = f"Slow response: {duration:.2f}ms"

                    status = HealthStatus.HEALTHY
                    if threshold_exceeded:
                        status = HealthStatus.DEGRADED

                    return HealthCheckResult(
                        component=self.name,
                        check_type="external_api",
                        status=status,
                        message="External API is accessible",
                        duration_ms=0,
                        timestamp=datetime.now(),
                        details=details,
                        threshold_exceeded=threshold_exceeded
                    )
                else:
                    return HealthCheckResult(
                        component=self.name,
                        check_type="external_api",
                        status=HealthStatus.UNHEALTHY,
                        message=f"API returned status {response.status_code}",
                        duration_ms=0,
                        timestamp=datetime.now(),
                        details={'status_code': response.status_code}
                    )

        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                check_type="external_api",
                status=HealthStatus.UNHEALTHY,
                message=f"External API check failed: {str(e)}",
                duration_ms=0,
                timestamp=datetime.now()
            )


class DiskSpaceHealthCheck(HealthCheck):
    """磁盘空间健康检查"""

    def __init__(self, mount_path: str = "/", warning_threshold: float = 80.0, critical_threshold: float = 90.0, **kwargs):
        super().__init__("disk_space", **kwargs)
        self.mount_path = mount_path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    async def execute_check(self) -> HealthCheckResult:
        try:
            import shutil

            total, used, free = shutil.disk_usage(self.mount_path)
            usage_percent = (used / total) * 100

            details = {
                'mount_path': self.mount_path,
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'usage_percent': round(usage_percent, 2)
            }

            # 确定健康状态
            status = HealthStatus.HEALTHY
            threshold_exceeded = None

            if usage_percent >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                threshold_exceeded = f"Critical: {usage_percent:.1f}% used (threshold: {self.critical_threshold}%)"
            elif usage_percent >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                threshold_exceeded = f"Warning: {usage_percent:.1f}% used (threshold: {self.warning_threshold}%)"

            message = f"Disk usage: {usage_percent:.1f}%"
            if threshold_exceeded:
                message += f" - {threshold_exceeded}"

            return HealthCheckResult(
                component=self.name,
                check_type="disk_space",
                status=status,
                message=message,
                duration_ms=0,
                timestamp=datetime.now(),
                details=details,
                threshold_exceeded=threshold_exceeded
            )

        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                check_type="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk space check failed: {str(e)}",
                duration_ms=0,
                timestamp=datetime.now()
            )


class MemoryHealthCheck(HealthCheck):
    """内存使用健康检查"""

    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 90.0, **kwargs):
        super().__init__("memory", **kwargs)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    async def execute_check(self) -> HealthCheckResult:
        try:
            import psutil

            memory = psutil.virtual_memory()
            usage_percent = memory.percent

            details = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'usage_percent': round(usage_percent, 2),
                'cached_gb': round(getattr(memory, 'cached', 0) / (1024**3), 2)
            }

            # 确定健康状态
            status = HealthStatus.HEALTHY
            threshold_exceeded = None

            if usage_percent >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                threshold_exceeded = f"Critical: {usage_percent:.1f}% used (threshold: {self.critical_threshold}%)"
            elif usage_percent >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                threshold_exceeded = f"Warning: {usage_percent:.1f}% used (threshold: {self.warning_threshold}%)"

            message = f"Memory usage: {usage_percent:.1f}%"
            if threshold_exceeded:
                message += f" - {threshold_exceeded}"

            return HealthCheckResult(
                component=self.name,
                check_type="memory",
                status=status,
                message=message,
                duration_ms=0,
                timestamp=datetime.now(),
                details=details,
                threshold_exceeded=threshold_exceeded
            )

        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                check_type="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {str(e)}",
                duration_ms=0,
                timestamp=datetime.now()
            )


class HealthMonitor:
    """健康监控器"""

    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.start_time = time.time()
        self.is_running = False
        self.check_interval = 60  # 默认60秒检查一次
        self.last_check_results: List[HealthCheckResult] = []
        self.health_history: List[SystemHealthSummary] = []
        self.max_history_size = 1000

    def add_check(self, check: HealthCheck):
        """添加健康检查"""
        self.checks[check.name] = check
        logger.info("health_check_added", check_name=check.name)

    def remove_check(self, check_name: str):
        """移除健康检查"""
        if check_name in self.checks:
            del self.checks[check_name]
            logger.info("health_check_removed", check_name=check_name)

    async def run_checks(self, level: CheckLevel = CheckLevel.STANDARD) -> SystemHealthSummary:
        """运行健康检查"""
        start_time = time.time()

        # 根据检查级别选择要执行的检查
        checks_to_run = self._get_checks_by_level(level)

        logger.info("health_checks_started",
                   total_checks=len(checks_to_run),
                   level=level.value)

        # 并发执行所有检查
        tasks = [check.check() for check in checks_to_run.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        check_results = []
        failed_checks = 0
        passed_checks = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 处理异常
                check_name = list(checks_to_run.keys())[i]
                error_result = HealthCheckResult(
                    component=check_name,
                    check_type="error",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check execution failed: {str(result)}",
                    duration_ms=0,
                    timestamp=datetime.now()
                )
                check_results.append(error_result)
                failed_checks += 1
                logger.error("health_check_execution_error",
                           check_name=check_name,
                           error=str(result))
            else:
                check_results.append(result)
                if result.status == HealthStatus.HEALTHY:
                    passed_checks += 1
                else:
                    failed_checks += 1

        # 计算整体状态
        overall_status = self._calculate_overall_status(check_results)

        # 计算性能指标
        performance_metrics = self._calculate_performance_metrics(check_results)

        # 创建健康摘要
        summary = SystemHealthSummary(
            overall_status=overall_status,
            timestamp=datetime.now(),
            total_checks=len(check_results),
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            check_results=check_results,
            service_uptime=time.time() - self.start_time,
            performance_metrics=performance_metrics
        )

        # 保存结果和历史
        self.last_check_results = check_results
        self.health_history.append(summary)

        # 限制历史记录大小
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size:]

        # 更新Prometheus指标
        self._update_metrics(summary)

        logger.info("health_checks_completed",
                   overall_status=overall_status.value,
                   passed_checks=passed_checks,
                   failed_checks=failed_checks,
                   duration_ms=(time.time() - start_time) * 1000)

        return summary

    def _get_checks_by_level(self, level: CheckLevel) -> Dict[str, HealthCheck]:
        """根据检查级别获取检查项"""
        if level == CheckLevel.BASIC:
            # 基础检查：只检查核心组件
            basic_checks = ['database', 'redis', 'memory']
            return {name: check for name, check in self.checks.items()
                   if name in basic_checks}
        elif level == CheckLevel.COMPREHENSIVE:
            # 全面检查：执行所有检查
            return self.checks.copy()
        else:
            # 标准检查：执行大部分检查
            standard_checks = ['database', 'redis', 'memory', 'disk_space']
            return {name: check for name, check in self.checks.items()
                   if name in standard_checks}

    def _calculate_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """计算整体健康状态"""
        if not results:
            return HealthStatus.UNKNOWN

        unhealthy_count = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for r in results if r.status == HealthStatus.DEGRADED)
        total_count = len(results)

        # 如果有超过50%的检查失败，则整体状态为不健康
        if unhealthy_count > total_count * 0.5:
            return HealthStatus.UNHEALTHY

        # 如果有不健康的检查，则整体状态为降级
        if unhealthy_count > 0:
            return HealthStatus.DEGRADED

        # 如果有降级的检查，则整体状态为降级
        if degraded_count > 0:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def _calculate_performance_metrics(self, results: List[HealthCheckResult]) -> Dict[str, float]:
        """计算性能指标"""
        if not results:
            return {}

        durations = [r.duration_ms for r in results]
        return {
            'avg_check_duration_ms': sum(durations) / len(durations),
            'max_check_duration_ms': max(durations),
            'min_check_duration_ms': min(durations),
            'success_rate': sum(1 for r in results if r.status == HealthStatus.HEALTHY) / len(results)
        }

    def _update_metrics(self, summary: SystemHealthSummary):
        """更新Prometheus指标"""
        try:
            # 更新服务可用性
            availability_value = 1.0 if summary.overall_status == HealthStatus.HEALTHY else 0.0
            service_availability.labels(service_name='overall').set(availability_value)

            # 更新错误率
            error_rate_value = (summary.failed_checks / summary.total_checks) if summary.total_checks > 0 else 0.0
            error_rate.labels(service_name='overall', error_type='health_check').set(error_rate_value)

            # 更新SLA合规性（基于健康状态）
            sla_compliance_value = availability_value  # 简化处理，实际应根据SLA要求计算
            sla_compliance.labels(sla_type='availability', time_period='current').set(sla_compliance_value)

        except Exception as e:
            logger.error("metrics_update_error", error=str(e))

    async def start_monitoring(self, interval: int = 60):
        """启动自动监控"""
        if self.is_running:
            return

        self.is_running = True
        self.check_interval = interval

        logger.info("health_monitoring_started", interval=interval)

        # 启动监控任务
        asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """停止自动监控"""
        self.is_running = False
        logger.info("health_monitoring_stopped")

    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                await self.run_checks(CheckLevel.STANDARD)
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error("monitoring_loop_error", error=str(e))
                await asyncio.sleep(min(self.check_interval, 30))  # 出错时减少检查频率

    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康摘要"""
        if not self.last_check_results:
            return {
                'status': 'unknown',
                'message': 'No health checks performed yet',
                'uptime_seconds': time.time() - self.start_time
            }

        latest_summary = self.health_history[-1] if self.health_history else None

        return {
            'overall_status': latest_summary.overall_status.value if latest_summary else 'unknown',
            'timestamp': latest_summary.timestamp.isoformat() if latest_summary else None,
            'total_checks': latest_summary.total_checks if latest_summary else 0,
            'passed_checks': latest_summary.passed_checks if latest_summary else 0,
            'failed_checks': latest_summary.failed_checks if latest_summary else 0,
            'service_uptime_seconds': time.time() - self.start_time,
            'monitoring_active': self.is_running,
            'check_interval': self.check_interval,
            'performance_metrics': latest_summary.performance_metrics if latest_summary else {},
            'individual_checks': [
                {
                    'component': result.component,
                    'status': result.status.value,
                    'message': result.message,
                    'duration_ms': result.duration_ms,
                    'last_check': result.timestamp.isoformat(),
                    'consecutive_failures': self.checks[result.component].consecutive_failures if result.component in self.checks else 0
                }
                for result in self.last_check_results
            ]
        }

    def get_health_trends(self, hours: int = 24) -> Dict[str, Any]:
        """获取健康趋势数据"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_history = [h for h in self.health_history if h.timestamp >= cutoff_time]

        if not recent_history:
            return {'message': f'No data available for the last {hours} hours'}

        # 计算趋势
        status_counts = {}
        for summary in recent_history:
            status = summary.overall_status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # 计算平均性能指标
        avg_performance = {}
        if recent_history:
            performance_keys = recent_history[0].performance_metrics.keys()
            for key in performance_keys:
                values = [h.performance_metrics.get(key, 0) for h in recent_history]
                avg_performance[key] = sum(values) / len(values) if values else 0

        return {
            'period_hours': hours,
            'total_checks': len(recent_history),
            'status_distribution': status_counts,
            'availability_percentage': (status_counts.get('healthy', 0) / len(recent_history)) * 100,
            'average_performance': avg_performance,
            'latest_check': recent_history[-1].timestamp.isoformat() if recent_history else None
        }


# 全局健康监控器实例
health_monitor = HealthMonitor()


# 便捷函数
async def initialize_health_monitoring(config: Dict[str, Any]):
    """初始化健康监控"""
    try:
        # 添加数据库检查
        if 'database_url' in config:
            health_monitor.add_check(
                DatabaseHealthCheck(config['database_url'])
            )

        # 添加Redis检查
        if 'redis_url' in config:
            health_monitor.add_check(
                RedisHealthCheck(config['redis_url'])
            )

        # 添加磁盘空间检查
        health_monitor.add_check(
            DiskSpaceHealthCheck(
                mount_path=config.get('disk_mount_path', '/'),
                warning_threshold=config.get('disk_warning_threshold', 80.0),
                critical_threshold=config.get('disk_critical_threshold', 90.0)
            )
        )

        # 添加内存检查
        health_monitor.add_check(
            MemoryHealthCheck(
                warning_threshold=config.get('memory_warning_threshold', 80.0),
                critical_threshold=config.get('memory_critical_threshold', 90.0)
            )
        )

        # 添加外部API检查
        if 'external_apis' in config:
            for api_name, api_url in config['external_apis'].items():
                health_monitor.add_check(
                    ExternalAPIHealthCheck(api_name, api_url)
                )

        # 启动监控
        await health_monitor.start_monitoring(
            interval=config.get('monitoring_interval', 60)
        )

        logger.info("health_monitoring_initialized",
                   total_checks=len(health_monitor.checks))

    except Exception as e:
        logger.error("health_monitoring_initialization_error", error=str(e))
        raise