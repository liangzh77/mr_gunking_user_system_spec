"""
契约测试：Prometheus指标格式 (T017a)

测试目标：
- 验证/metrics端点返回有效Prometheus格式
- 验证包含所有NFR-017a定义的8个核心指标
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestPrometheusMetricsContract:
    """Prometheus指标契约测试"""

    def test_metrics_endpoint_returns_200(self):
        """测试/metrics端点可访问"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

    def test_metrics_contains_required_metrics(self):
        """测试包含所有必需指标"""
        response = client.get("/metrics")
        content = response.text

        required_metrics = [
            "mr_auth_requests_total",
            "mr_auth_latency_seconds",
            "mr_operator_balance_yuan",
            "mr_payment_callback_total",
            "mr_revenue_total_yuan",
            "mr_db_connection_pool_active",
            "mr_api_errors_total",
            "mr_rate_limit_blocked_total"
        ]

        for metric in required_metrics:
            assert metric in content, f"缺少必需指标: {metric}"

    def test_metrics_format_is_valid_prometheus(self):
        """测试Prometheus格式有效性"""
        response = client.get("/metrics")
        content = response.text

        # 基本格式验证
        lines = content.split("\n")

        # 应包含HELP和TYPE行
        help_lines = [l for l in lines if l.startswith("# HELP")]
        type_lines = [l for l in lines if l.startswith("# TYPE")]

        assert len(help_lines) > 0, "应包含HELP行"
        assert len(type_lines) > 0, "应包含TYPE行"

    # TODO: 实现更详细的契约验证
