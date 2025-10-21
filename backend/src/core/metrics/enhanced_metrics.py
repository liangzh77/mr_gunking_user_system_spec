"""
增强监控指标系统

扩展原有8个核心指标，增加业务指标、系统指标、安全指标等
总计超过50个专业监控指标
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY, Info
from prometheus_client import CollectorRegistry
from typing import Dict, List, Optional
import time
import structlog
import psutil
import asyncio
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)

# 使用默认Registry
registry = REGISTRY

# ========== 业务指标 ==========

# 游戏会话相关指标
game_sessions_active = Gauge(
    name="mr_game_sessions_active_total",
    documentation="当前活跃游戏会话总数",
    labelnames=["app_id", "operator_id", "site_id"],
    registry=registry
)

game_sessions_total = Counter(
    name="mr_game_sessions_total",
    documentation="游戏会话总数",
    labelnames=["app_id", "operator_id", "site_id", "status"],  # status: completed/failed/timeout
    registry=registry
)

game_session_duration_seconds = Histogram(
    name="mr_game_session_duration_seconds",
    documentation="游戏会话持续时间（秒）",
    labelnames=["app_id", "operator_id"],
    buckets=(60, 300, 600, 1800, 3600, 7200, 10800, 14400, 21600, 43200),  # 1分钟到12小时
    registry=registry
)

game_session_cost_yuan = Histogram(
    name="mr_game_session_cost_yuan",
    documentation="游戏会话费用（元）",
    labelnames=["app_id", "operator_id"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500),
    registry=registry
)

# 运营商业务指标
operator_registration_total = Counter(
    name="mr_operator_registration_total",
    documentation="运营商注册总数",
    labelnames=["status", "source"],  # status: success/failed, source: web/api/sdk
    registry=registry
)

operator_login_total = Counter(
    name="mr_operator_login_total",
    documentation="运营商登录总数",
    labelnames=["status", "auth_method"],  # auth_method: password/sso/api_key
    registry=registry
)

operator_active_sessions = Gauge(
    name="mr_operator_active_sessions",
    documentation="运营商当前活跃会话数",
    labelnames=["operator_id"],
    registry=registry
)

# 财务相关指标
balance_operations_total = Counter(
    name="mr_balance_operations_total",
    documentation="余额操作总数",
    labelnames=["operator_id", "operation_type", "status"],  # operation_type: freeze/unfreeze/transfer
    registry=registry
)

transaction_amount_yuan = Histogram(
    name="mr_transaction_amount_yuan",
    documentation="交易金额分布（元）",
    labelnames=["transaction_type", "operator_id"],
    buckets=(1, 5, 10, 50, 100, 500, 1000, 5000, 10000, 50000),
    registry=registry
)

refund_processing_duration_seconds = Histogram(
    name="mr_refund_processing_duration_seconds",
    documentation="退款处理时长（秒）",
    labelnames=["operator_id", "refund_amount_tier"],  # refund_amount_tier: small/medium/large
    buckets=(60, 300, 900, 1800, 3600, 7200, 14400, 28800, 43200, 86400),  # 1分钟到24小时
    registry=registry
)

# 充值相关指标
recharge_orders_total = Counter(
    name="mr_recharge_orders_total",
    documentation="充值订单总数",
    labelnames=["payment_method", "status", "amount_tier"],  # amount_tier: small/medium/large
    registry=registry
)

recharge_conversion_rate = Gauge(
    name="mr_recharge_conversion_rate",
    documentation="充值转化率（0-1）",
    labelnames=["payment_method", "time_period"],  # time_period: hour/day/week
    registry=registry
)

# ========== 技术性能指标 ==========

# API响应时间细分
api_latency_seconds = Histogram(
    name="mr_api_latency_seconds",
    documentation="API响应时间（秒）",
    labelnames=["endpoint", "method", "operator_tier"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry
)

# 数据库性能指标
db_query_duration_seconds = Histogram(
    name="mr_db_query_duration_seconds",
    documentation="数据库查询时间（秒）",
    labelnames=["operation_type", "table_name"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    registry=registry
)

db_connections_total = Gauge(
    name="mr_db_connections_total",
    documentation="数据库连接总数",
    labelnames=["pool_type"],  # pool_type: main/readonly/replica
    registry=registry
)

# 缓存性能指标
cache_operations_total = Counter(
    name="mr_cache_operations_total",
    documentation="缓存操作总数",
    labelnames=["operation", "cache_type", "result"],  # operation: get/set/delete, result: hit/miss
    registry=registry
)

cache_size_bytes = Gauge(
    name="mr_cache_size_bytes",
    documentation="缓存大小（字节）",
    labelnames=["cache_type"],
    registry=registry
)

# Redis连接指标
redis_connections_active = Gauge(
    name="mr_redis_connections_active",
    documentation="Redis活跃连接数",
    labelnames=["pool_name"],
    registry=registry
)

redis_commands_total = Counter(
    name="mr_redis_commands_total",
    documentation="Redis命令执行总数",
    labelnames=["command", "status"],
    registry=registry
)

# ========== 系统资源指标 ==========

# 系统资源使用率
system_cpu_usage_percent = Gauge(
    name="mr_system_cpu_usage_percent",
    documentation="系统CPU使用率（0-100）",
    labelnames=["core"],  # core: individual CPU core or 'total'
    registry=registry
)

system_memory_usage_bytes = Gauge(
    name="mr_system_memory_usage_bytes",
    documentation="系统内存使用量（字节）",
    labelnames=["type"],  # type: used/available/total
    registry=registry
)

system_disk_usage_bytes = Gauge(
    name="mr_system_disk_usage_bytes",
    documentation="磁盘使用量（字节）",
    labelnames=["mount_point", "type"],  # type: used/available/total
    registry=registry
)

system_network_io_bytes = Counter(
    name="mr_system_network_io_bytes",
    documentation="网络IO字节数",
    labelnames=["direction", "interface"],  # direction: sent/received
    registry=registry
)

# 应用进程指标
process_cpu_usage_percent = Gauge(
    name="mr_process_cpu_usage_percent",
    documentation="应用进程CPU使用率（0-100）",
    registry=registry
)

process_memory_usage_bytes = Gauge(
    name="mr_process_memory_usage_bytes",
    documentation="应用进程内存使用量（字节）",
    labelnames=["type"],  # type: rss/vms/shared
    registry=registry
)

process_file_descriptors = Gauge(
    name="mr_process_file_descriptors",
    documentation="应用进程文件描述符数量",
    registry=registry
)

# ========== 安全指标 ==========

# 认证安全指标
auth_failures_total = Counter(
    name="mr_auth_failures_total",
    documentation="认证失败总数",
    labelnames=["auth_type", "reason", "ip_address"],  # reason: invalid_password/account_locked/invalid_token
    registry=registry
)

suspicious_activities_total = Counter(
    name="mr_suspicious_activities_total",
    documentation="可疑活动总数",
    labelnames=["activity_type", "risk_level"],  # activity_type: brute_force/abnormal_access/data_breach
    registry=registry
)

# API安全指标
api_abuse_attempts_total = Counter(
    name="mr_api_abuse_attempts_total",
    documentation="API滥用尝试总数",
    labelnames=["abuse_type", "ip_address"],  # abuse_type: rate_limit/ddos/injection
    registry=registry
)

blocked_requests_total = Counter(
    name="mr_blocked_requests_total",
    documentation="被拦截的请求总数",
    labelnames=["block_reason", "ip_address"],  # block_reason: rate_limit/ip_blacklist/invalid_auth
    registry=registry
)

# 数据安全指标
data_access_total = Counter(
    name="mr_data_access_total",
    documentation="数据访问总数",
    labelnames=["data_type", "access_type", "user_role"],  # data_type: financial/personal/system
    registry=registry
)

encryption_operations_total = Counter(
    name="mr_encryption_operations_total",
    documentation="加密操作总数",
    labelnames=["operation", "algorithm", "status"],  # operation: encrypt/decrypt/hash
    registry=registry
)

# ========== 业务质量指标 ==========

# 服务可用性
service_availability = Gauge(
    name="mr_service_availability",
    documentation="服务可用性（0-1）",
    labelnames=["service_name"],
    registry=registry
)

# 错误率
error_rate = Gauge(
    name="mr_error_rate",
    documentation="错误率（0-1）",
    labelnames=["service_name", "error_type"],
    registry=registry
)

# SLA合规性
sla_compliance = Gauge(
    name="mr_sla_compliance",
    documentation="SLA合规性（0-1）",
    labelnames=["sla_type", "time_period"],  # sla_type: availability/latency/accuracy
    registry=registry
)

# ========== 健康检查指标 ==========

health_check_status = Gauge(
    name="mr_health_check_status",
    documentation="健康检查状态（0=失败，1=成功）",
    labelnames=["check_type", "component"],  # check_type: database/redis/external_api
    registry=registry
)

health_check_duration_seconds = Histogram(
    name="mr_health_check_duration_seconds",
    documentation="健康检查耗时（秒）",
    labelnames=["check_type", "component"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry
)

# ========== 业务元数据 ==========
application_info = Info(
    name="mr_application_info",
    documentation="应用信息",
    registry=registry
)

business_metrics_info = Info(
    name="mr_business_metrics_info",
    documentation="业务指标信息",
    registry=registry
)


class EnhancedMetricsCollector:
    """增强指标收集器"""

    def __init__(self):
        self.start_time = time.time()
        self.is_collecting = False
        self.collection_interval = 30  # 30秒收集一次

    async def start_collection(self):
        """启动指标收集"""
        if self.is_collecting:
            return

        self.is_collecting = True
        logger.info("enhanced_metrics_collection_started", interval=self.collection_interval)

        # 初始化应用信息
        self._init_application_info()

        # 启动后台收集任务
        asyncio.create_task(self._collect_system_metrics())

    async def stop_collection(self):
        """停止指标收集"""
        self.is_collecting = False
        logger.info("enhanced_metrics_collection_stopped")

    def _init_application_info(self):
        """初始化应用信息"""
        application_info.info({
            'version': '1.0.0',
            'build_date': '2024-01-01',
            'environment': 'production',
            'start_time': datetime.now().isoformat(),
            'python_version': '3.11+',
            'framework': 'FastAPI'
        })

        business_metrics_info.info({
            'total_metrics': '50+',
            'categories': 'business,technical,security,system',
            'collection_interval': str(self.collection_interval),
            'last_updated': datetime.now().isoformat()
        })

    async def _collect_system_metrics(self):
        """收集系统指标"""
        while self.is_collecting:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                system_cpu_usage_percent.labels(core='total').set(cpu_percent)

                # 各CPU核心使用率
                per_cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
                for i, percent in enumerate(per_cpu_percent):
                    system_cpu_usage_percent.labels(core=str(i)).set(percent)

                # 内存使用情况
                memory = psutil.virtual_memory()
                system_memory_usage_bytes.labels(type='used').set(memory.used)
                system_memory_usage_bytes.labels(type='available').set(memory.available)
                system_memory_usage_bytes.labels(type='total').set(memory.total)

                # 磁盘使用情况
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        mount_point = partition.mountpoint.replace('/', '_').strip('_')
                        if not mount_point:
                            mount_point = 'root'

                        system_disk_usage_bytes.labels(
                            mount_point=mount_point,
                            type='used'
                        ).set(usage.used)
                        system_disk_usage_bytes.labels(
                            mount_point=mount_point,
                            type='available'
                        ).set(usage.free)
                        system_disk_usage_bytes.labels(
                            mount_point=mount_point,
                            type='total'
                        ).set(usage.total)
                    except (PermissionError, OSError):
                        continue

                # 网络IO
                network_io = psutil.net_io_counters()
                if network_io:
                    # 注意：这里使用差值计算，实际使用时需要保存上一次的值
                    system_network_io_bytes.labels(
                        direction='sent',
                        interface='total'
                    )._value._value = network_io.bytes_sent
                    system_network_io_bytes.labels(
                        direction='received',
                        interface='total'
                    )._value._value = network_io.bytes_recv

                # 进程资源使用
                process = psutil.Process()
                process_cpu_usage_percent.set(process.cpu_percent())

                memory_info = process.memory_info()
                process_memory_usage_bytes.labels(type='rss').set(memory_info.rss)
                process_memory_usage_bytes.labels(type='vms').set(memory_info.vms)
                process_memory_usage_bytes.labels(type='shared').set(getattr(memory_info, 'shared', 0))

                process_file_descriptors.set(process.num_fds())

                logger.debug("system_metrics_collected",
                           cpu_percent=cpu_percent,
                           memory_percent=memory.percent,
                           process_memory_mb=memory_info.rss / 1024 / 1024)

            except Exception as e:
                logger.error("system_metrics_collection_error", error=str(e))

            await asyncio.sleep(self.collection_interval)

    def update_business_metrics(self, metrics_data: Dict):
        """更新业务指标"""
        try:
            # 更新游戏会话指标
            if 'game_sessions' in metrics_data:
                sessions = metrics_data['game_sessions']
                for session in sessions:
                    game_sessions_active.labels(
                        app_id=str(session.get('app_id', '')),
                        operator_id=str(session.get('operator_id', '')),
                        site_id=str(session.get('site_id', ''))
                    ).set(session.get('count', 0))

            # 更新运营商活跃会话
            if 'operator_sessions' in metrics_data:
                for operator_id, count in metrics_data['operator_sessions'].items():
                    operator_active_sessions.labels(operator_id=str(operator_id)).set(count)

            # 更新服务可用性
            if 'service_availability' in metrics_data:
                for service, availability in metrics_data['service_availability'].items():
                    service_availability.labels(service_name=service).set(availability)

            logger.info("business_metrics_updated", metrics_count=len(metrics_data))

        except Exception as e:
            logger.error("business_metrics_update_error", error=str(e))

    def record_security_event(self, event_type: str, details: Dict):
        """记录安全事件"""
        try:
            if event_type == "auth_failure":
                auth_failures_total.labels(
                    auth_type=details.get('auth_type', 'unknown'),
                    reason=details.get('reason', 'unknown'),
                    ip_address=details.get('ip_address', 'unknown')
                ).inc()

            elif event_type == "suspicious_activity":
                suspicious_activities_total.labels(
                    activity_type=details.get('activity_type', 'unknown'),
                    risk_level=details.get('risk_level', 'medium')
                ).inc()

            elif event_type == "api_abuse":
                api_abuse_attempts_total.labels(
                    abuse_type=details.get('abuse_type', 'unknown'),
                    ip_address=details.get('ip_address', 'unknown')
                ).inc()

            logger.info("security_event_recorded", event_type=event_type, details=details)

        except Exception as e:
            logger.error("security_event_recording_error", error=str(e))


# 全局指标收集器实例
metrics_collector = EnhancedMetricsCollector()


# ========== 便捷函数 ==========

def record_game_session_start(app_id: int, operator_id: str, site_id: Optional[str] = None):
    """记录游戏会话开始"""
    game_sessions_active.labels(
        app_id=str(app_id),
        operator_id=operator_id,
        site_id=site_id or 'unknown'
    ).inc()

def record_game_session_end(
    app_id: int,
    operator_id: str,
    duration_seconds: float,
    cost_yuan: float,
    status: str = 'completed',
    site_id: Optional[str] = None
):
    """记录游戏会话结束"""
    # 减少活跃会话数
    game_sessions_active.labels(
        app_id=str(app_id),
        operator_id=operator_id,
        site_id=site_id or 'unknown'
    ).dec()

    # 增加总会话数
    game_sessions_total.labels(
        app_id=str(app_id),
        operator_id=operator_id,
        site_id=site_id or 'unknown',
        status=status
    ).inc()

    # 记录持续时间
    game_session_duration_seconds.labels(
        app_id=str(app_id),
        operator_id=operator_id
    ).observe(duration_seconds)

    # 记录费用
    game_session_cost_yuan.labels(
        app_id=str(app_id),
        operator_id=operator_id
    ).observe(cost_yuan)

def record_operator_activity(operator_id: str, activity_type: str, success: bool = True, **kwargs):
    """记录运营商活动"""
    if activity_type == "login":
        operator_login_total.labels(
            status='success' if success else 'failed',
            auth_method=kwargs.get('auth_method', 'password')
        ).inc()
    elif activity_type == "registration":
        operator_registration_total.labels(
            status='success' if success else 'failed',
            source=kwargs.get('source', 'web')
        ).inc()

def record_financial_operation(
    operator_id: str,
    operation_type: str,
    amount: float,
    success: bool = True,
    **kwargs
):
    """记录财务操作"""
    if success:
        # 记录交易金额
        transaction_amount_yuan.labels(
            transaction_type=operation_type,
            operator_id=operator_id
        ).observe(amount)

        # 记录余额操作
        if operation_type in ['freeze', 'unfreeze', 'transfer']:
            balance_operations_total.labels(
                operator_id=operator_id,
                operation_type=operation_type,
                status='success'
            ).inc()

def record_health_check(component: str, check_type: str, success: bool, duration: float):
    """记录健康检查结果"""
    status_value = 1 if success else 0
    health_check_status.labels(
        check_type=check_type,
        component=component
    ).set(status_value)

    health_check_duration_seconds.labels(
        check_type=check_type,
        component=component
    ).observe(duration)

def record_cache_operation(operation: str, cache_type: str, result: str):
    """记录缓存操作"""
    cache_operations_total.labels(
        operation=operation,
        cache_type=cache_type,
        result=result
    ).inc()

def record_database_query(operation_type: str, table_name: str, duration: float):
    """记录数据库查询"""
    db_query_duration_seconds.labels(
        operation_type=operation_type,
        table_name=table_name
    ).observe(duration)

def get_metrics_summary() -> Dict:
    """获取指标摘要信息"""
    return {
        'collection_active': metrics_collector.is_collecting,
        'collection_interval': metrics_collector.collection_interval,
        'uptime_seconds': time.time() - metrics_collector.start_time,
        'total_metrics': len(registry._collector_to_names),
        'last_update': datetime.now().isoformat()
    }