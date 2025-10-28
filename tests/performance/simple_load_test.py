#!/usr/bin/env python3
"""
简化版负载测试脚本 - 使用locust命令行方式
"""

from locust import HttpUser, task, between
import random
import json


class SimpleLoadTest(HttpUser):
    """简化版负载测试用户"""

    wait_time = between(1, 3)  # 用户操作间隔1-3秒

    def on_start(self):
        """用户开始时的初始化操作"""
        pass  # 暂时跳过登录，直接测试公开端点

    @task(5)
    def health_check(self):
        """健康检查"""
        self.client.get("/health")

    @task(3)
    def test_api_docs(self):
        """测试API文档"""
        try:
            self.client.get("/api/docs")
        except:
            pass  # 如果API文档不可访问，忽略错误

    @task(2)
    def test_admin_endpoints(self):
        """测试管理员端点（预期会失败）"""
        try:
            # 这些端点应该返回401未授权
            self.client.get("/api/v1/admin/operators")
        except:
            pass

    @task(1)
    def test_random_endpoint(self):
        """测试随机端点"""
        endpoints = [
            "/health",
            "/metrics",
            "/api/v1/admin/operators",
            "/api/v1/admin/applications"
        ]
        endpoint = random.choice(endpoints)
        try:
            self.client.get(endpoint)
        except:
            pass


if __name__ == "__main__":
    print("使用locust命令行运行负载测试:")
    print("locust -f tests/performance/simple_load_test.py --host http://localhost:8000")