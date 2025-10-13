"""
Prometheus监控指标中间件

实现NFR-017a定义的8个核心指标：
1. mr_auth_requests_total - 授权请求总数
2. mr_auth_latency_seconds - 授权接口延迟
3. mr_operator_balance_yuan - 运营商余额
4. mr_payment_callback_total - 支付回调计数
5. mr_revenue_total_yuan - 总收入
6. mr_db_connection_pool_active - 数据库连接池活跃连接数
7. mr_api_errors_total - API错误计数
8. mr_rate_limit_blocked_total - 频率限制拦截计数
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client import CollectorRegistry
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
import time
import structlog

logger = structlog.get_logger(__name__)

# 使用默认Registry
registry = REGISTRY

# ========== 1. 授权请求计数器 ==========
auth_requests_total = Counter(
    name="mr_auth_requests_total",
    documentation="Total number of game authorization requests",
    labelnames=["operator_id", "application_code", "status"],  # status: success/failed
    registry=registry
)

# ========== 2. 授权接口延迟直方图 ==========
auth_latency_seconds = Histogram(
    name="mr_auth_latency_seconds",
    documentation="Game authorization API latency in seconds",
    labelnames=["operator_id", "application_code"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0),  # P95 <100ms
    registry=registry
)

# ========== 3. 运营商余额Gauge ==========
operator_balance_yuan = Gauge(
    name="mr_operator_balance_yuan",
    documentation="Current balance of operator account in CNY",
    labelnames=["operator_id", "username", "customer_tier"],
    registry=registry
)

# ========== 4. 支付回调计数器 ==========
payment_callback_total = Counter(
    name="mr_payment_callback_total",
    documentation="Total number of payment callbacks received",
    labelnames=["channel", "status"],  # channel: wechat/alipay, status: success/failed
    registry=registry
)

# ========== 5. 总收入计数器 ==========
revenue_total_yuan = Counter(
    name="mr_revenue_total_yuan",
    documentation="Total revenue collected in CNY",
    labelnames=["transaction_type"],  # recharge/consumption/refund
    registry=registry
)

# ========== 6. 数据库连接池Gauge ==========
db_connection_pool_active = Gauge(
    name="mr_db_connection_pool_active",
    documentation="Number of active database connections in pool",
    registry=registry
)

db_connection_pool_idle = Gauge(
    name="mr_db_connection_pool_idle",
    documentation="Number of idle database connections in pool",
    registry=registry
)

# ========== 7. API错误计数器 ==========
api_errors_total = Counter(
    name="mr_api_errors_total",
    documentation="Total number of API errors",
    labelnames=["endpoint", "method", "status_code", "error_type"],
    registry=registry
)

# ========== 8. 频率限制拦截计数器 ==========
rate_limit_blocked_total = Counter(
    name="mr_rate_limit_blocked_total",
    documentation="Total number of requests blocked by rate limiter",
    labelnames=["limit_type", "identifier"],  # limit_type: operator/ip
    registry=registry
)

# ========== 额外指标：HTTP请求总数 ==========
http_requests_total = Counter(
    name="mr_http_requests_total",
    documentation="Total number of HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
    registry=registry
)

# ========== 额外指标：HTTP请求延迟 ==========
http_request_duration_seconds = Histogram(
    name="mr_http_request_duration_seconds",
    documentation="HTTP request latency in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=registry
)


class PrometheusMiddleware:
    """
    Prometheus监控中间件

    功能：
    - 自动记录HTTP请求指标
    - 记录响应时间
    - 捕获错误并计数
    """

    async def __call__(self, request: Request, call_next):
        """处理请求并记录指标"""
        # 排除/metrics端点本身
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()
        method = request.method
        endpoint = request.url.path

        try:
            # 执行请求
            response = await call_next(request)
            status_code = response.status_code

            # 记录请求计数
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()

            # 记录延迟
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # 如果是错误响应，记录错误指标
            if status_code >= 400:
                api_errors_total.labels(
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    error_type="http_error"
                ).inc()

            return response

        except Exception as e:
            # 捕获未处理的异常
            duration = time.time() - start_time

            api_errors_total.labels(
                endpoint=endpoint,
                method=method,
                status_code=500,
                error_type=type(e).__name__
            ).inc()

            logger.error(
                "unhandled_exception_in_middleware",
                endpoint=endpoint,
                method=method,
                error=str(e),
                duration=duration
            )

            raise


async def metrics_endpoint(request: Request):
    """
    /metrics端点：暴露Prometheus指标

    Returns:
        text/plain格式的Prometheus指标数据
    """
    metrics_data = generate_latest(registry)
    return PlainTextResponse(
        content=metrics_data,
        media_type="text/plain; version=0.0.4"
    )


def setup_prometheus_metrics(app):
    """
    配置FastAPI应用的Prometheus监控

    Args:
        app: FastAPI应用实例

    Example:
        from fastapi import FastAPI
        app = FastAPI()
        setup_prometheus_metrics(app)
    """
    # 注册中间件
    app.middleware("http")(PrometheusMiddleware())

    # 注册/metrics端点
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])

    logger.info(
        "prometheus_metrics_configured",
        endpoint="/metrics",
        metrics_count=8
    )


# ========== 工具函数：手动记录指标 ==========

def record_auth_request(
    operator_id: str,
    application_code: str,
    success: bool,
    duration_seconds: float
):
    """
    记录授权请求指标

    Args:
        operator_id: 运营商ID
        application_code: 应用代码
        success: 是否成功
        duration_seconds: 处理时长（秒）
    """
    status = "success" if success else "failed"

    auth_requests_total.labels(
        operator_id=operator_id,
        application_code=application_code,
        status=status
    ).inc()

    auth_latency_seconds.labels(
        operator_id=operator_id,
        application_code=application_code
    ).observe(duration_seconds)


def update_operator_balance_metric(
    operator_id: str,
    username: str,
    customer_tier: str,
    balance: float
):
    """
    更新运营商余额指标

    Args:
        operator_id: 运营商ID
        username: 用户名
        customer_tier: 客户分类
        balance: 当前余额（元）
    """
    operator_balance_yuan.labels(
        operator_id=operator_id,
        username=username,
        customer_tier=customer_tier
    ).set(balance)


def record_payment_callback(channel: str, success: bool):
    """
    记录支付回调

    Args:
        channel: 支付渠道 (wechat/alipay)
        success: 是否成功
    """
    status = "success" if success else "failed"
    payment_callback_total.labels(channel=channel, status=status).inc()


def record_revenue(transaction_type: str, amount: float):
    """
    记录收入

    Args:
        transaction_type: 交易类型 (recharge/consumption/refund)
        amount: 金额（元）
    """
    revenue_total_yuan.labels(transaction_type=transaction_type).inc(amount)


def update_db_pool_metrics(active: int, idle: int):
    """
    更新数据库连接池指标

    Args:
        active: 活跃连接数
        idle: 空闲连接数
    """
    db_connection_pool_active.set(active)
    db_connection_pool_idle.set(idle)


def record_rate_limit_block(limit_type: str, identifier: str):
    """
    记录频率限制拦截

    Args:
        limit_type: 限制类型 (operator/ip)
        identifier: 标识符
    """
    rate_limit_blocked_total.labels(
        limit_type=limit_type,
        identifier=identifier
    ).inc()
