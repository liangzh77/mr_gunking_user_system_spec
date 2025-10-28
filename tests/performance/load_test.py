#!/usr/bin/env python3
"""
MR游戏运营管理系统 - 负载测试和压力测试脚本

使用locust进行负载测试，模拟真实用户场景。
测试范围：
1. 管理员登录和面板访问
2. 运营商管理操作
3. 应用管理操作
4. 财务管理操作
5. API接口性能测试

运行方式：
# 单用户测试
python tests/performance/load_test.py --users 1 --spawn-rate 1 --host http://localhost:8000

# 中等负载测试 (50并发用户)
python tests/performance/load_test.py --users 50 --spawn-rate 5 --host http://localhost:8000

# 高负载测试 (200并发用户)
python tests/performance/load_test.py --users 200 --spawn-rate 20 --host http://localhost:8000

# 压力测试 (500并发用户)
python tests/performance/load_test.py --users 500 --spawn-rate 50 --host http://localhost:8000 --run-time 300s
"""

import asyncio
import json
import random
import time
from typing import Dict, List
import argparse
from contextlib import asynccontextmanager

try:
    from locust import HttpUser, task, between, events
    from locust.env import Environment
    from locust.stats import stats_printer, stats_history
    from locust.log import setup_logging
except ImportError:
    print("请安装locust: pip install locust")
    exit(1)

import httpx
import jwt
from datetime import datetime, timedelta


class MRGameOpsUser(HttpUser):
    """MR游戏运营管理系统用户模拟"""

    wait_time = between(1, 3)  # 用户操作间隔1-3秒

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.user_type = None  # admin, operator, finance
        self.operator_id = None
        self.app_id = None

    def on_start(self):
        """用户开始时的初始化操作"""
        self.user_type = random.choice(['admin', 'operator', 'finance'])
        if self.user_type == 'admin':
            self.admin_login()
        elif self.user_type == 'operator':
            self.operator_login()
        else:
            self.finance_login()

    def admin_login(self) -> bool:
        """管理员登录"""
        try:
            response = self.client.post("/api/v1/admin/auth/login", json={
                "username": "admin",
                "password": "admin123456"
            })

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.client.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                return True
            else:
                print(f"管理员登录失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"管理员登录异常: {e}")
            return False

    def operator_login(self) -> bool:
        """运营商登录"""
        try:
            response = self.client.post("/api/v1/auth/login", json={
                "username": "operator1",
                "password": "password123"
            })

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.client.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                return True
            else:
                print(f"运营商登录失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"运营商登录异常: {e}")
            return False

    def finance_login(self) -> bool:
        """财务登录"""
        try:
            response = self.client.post("/api/v1/finance/auth/login", json={
                "username": "finance1",
                "password": "finance123"
            })

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.client.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                return True
            else:
                print(f"财务登录失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"财务登录异常: {e}")
            return False

    @task(3)
    def view_dashboard(self):
        """查看仪表板"""
        if self.user_type == 'admin':
            self.client.get("/api/v1/admin/dashboard/stats")
        elif self.user_type == 'operator':
            self.client.get("/api/v1/operations/dashboard")

    @task(2)
    def list_operators(self):
        """查看运营商列表"""
        if self.user_type == 'admin':
            self.client.get("/api/v1/admin/operators")

    @task(2)
    def list_applications(self):
        """查看应用列表"""
        if self.user_type == 'admin':
            self.client.get("/api/v1/admin/applications")

    @task(2)
    def view_transactions(self):
        """查看交易记录"""
        if self.user_type == 'admin':
            self.client.get("/api/v1/admin/transactions")
        elif self.user_type == 'finance':
            self.client.get("/api/v1/finance/transactions")

    @task(1)
    def view_refunds(self):
        """查看退款记录"""
        if self.user_type == 'admin':
            self.client.get("/api/v1/admin/refunds")
        elif self.user_type == 'finance':
            self.client.get("/api/v1/finance/refunds")

    @task(1)
    def view_invoices(self):
        """查看发票记录"""
        if self.user_type == 'admin':
            self.client.get("/api/v1/admin/invoices")
        elif self.user_type == 'finance':
            self.client.get("/api/v1/finance/invoices")

    @task(1)
    def create_operator_site(self):
        """创建运营点（仅管理员）"""
        if self.user_type == 'admin' and random.random() < 0.1:  # 10%概率执行
            site_data = {
                "name": f"测试运营点{random.randint(1000, 9999)}",
                "address": f"测试地址{random.randint(100, 999)}号",
                "description": "负载测试创建的运营点",
                "operator_id": "test-operator-id"
            }
            self.client.post("/api/v1/admin/sites", json=site_data)

    @task(1)
    def create_application(self):
        """创建应用（仅管理员）"""
        if self.user_type == 'admin' and random.random() < 0.1:  # 10%概率执行
            app_data = {
                "app_code": f"test_app_{random.randint(1000, 9999)}",
                "app_name": f"测试应用{random.randint(1000, 9999)}",
                "description": "负载测试创建的应用",
                "unit_price": random.uniform(1.0, 100.0),
                "min_players": random.randint(1, 5),
                "max_players": random.randint(10, 50)
            }
            self.client.post("/api/v1/admin/applications", json=app_data)

    @task(5)
    def health_check(self):
        """健康检查"""
        self.client.get("/health")

    @task(3)
    def get_metrics(self):
        """获取监控指标"""
        self.client.get("/metrics")


class StressTestUser(HttpUser):
    """压力测试用户 - 专门用于极限测试"""

    wait_time = between(0.1, 0.5)  # 更快的操作间隔

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def on_start(self):
        """快速登录"""
        try:
            response = self.client.post("/api/v1/admin/auth/login", json={
                "username": "admin",
                "password": "admin123456"
            })

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.client.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
        except:
            pass  # 压力测试时忽略登录失败

    @task(10)
    def rapid_api_calls(self):
        """快速API调用"""
        endpoints = [
            "/api/v1/admin/dashboard/stats",
            "/api/v1/admin/operators",
            "/api/v1/admin/applications",
            "/api/v1/admin/transactions",
            "/health",
            "/metrics"
        ]
        endpoint = random.choice(endpoints)
        self.client.get(endpoint)

    @task(5)
    def concurrent_operations(self):
        """并发操作测试"""
        operations = [
            lambda: self.client.get("/api/v1/admin/operators"),
            lambda: self.client.get("/api/v1/admin/applications"),
            lambda: self.client.get("/api/v1/admin/transactions"),
        ]

        # 随机选择1-3个操作同时执行
        selected_ops = random.sample(operations, random.randint(1, 3))
        for op in selected_ops:
            try:
                op()
            except:
                pass


def on_request_success(request_type, name, response_time, response_length, **kwargs):
    """请求成功回调"""
    print(f"✓ {request_type} {name} - {response_time:.2f}ms - {response_length}B")


def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """请求失败回调"""
    print(f"✗ {request_type} {name} - {response_time:.2f}ms - {exception}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MR游戏运营管理系统负载测试")
    parser.add_argument("--host", default="http://localhost:8000", help="目标服务器地址")
    parser.add_argument("--users", type=int, default=10, help="并发用户数")
    parser.add_argument("--spawn-rate", type=int, default=2, help="用户生成速率")
    parser.add_argument("--run-time", default="60s", help="运行时间")
    parser.add_argument("--stress", action="store_true", help="启用压力测试模式")
    parser.add_argument("--html", default="reports/report.html", help="HTML报告输出路径")

    args = parser.parse_args()

    # 设置事件监听器
    try:
        events.request_success.add_listener(on_request_success)
        events.request_failure.add_listener(on_request_failure)
    except AttributeError:
        # 新版本locust可能使用不同的事件API
        pass

    # 设置环境
    env = Environment(web_host=args.host)

    if args.stress:
        # 压力测试模式
        env.user_class = StressTestUser
        print(f"🚀 启动压力测试: {args.users} 用户, 生成速率 {args.spawn_rate}/s")
    else:
        # 正常负载测试
        env.user_class = MRGameOpsUser
        print(f"📊 启动负载测试: {args.users} 用户, 生成速率 {args.spawn_rate}/s")

    # 创建用户
    env.create_local_runner()
    env.runner.start(args.users, spawn_rate=args.spawn_rate)

    # 运行指定时间
    run_time_seconds = int(args.run_time.rstrip('s'))
    print(f"⏱️  运行时间: {args.run_time}")
    time.sleep(run_time_seconds)

    # 停止测试
    env.runner.stop()
    env.runner.greenlet.join()

    # 生成统计信息
    print("\n" + "="*50)
    print("📈 测试统计信息")
    print("="*50)

    stats = env.runner.stats

    print(f"总请求数: {stats.total.num_requests}")
    print(f"失败请求数: {stats.total.num_failures}")
    print(f"成功率: {(stats.total.num_requests / (stats.total.num_requests + stats.total.num_failures) * 100):.2f}%")

    if stats.total.num_requests > 0:
        print(f"平均响应时间: {stats.total.avg_response_time:.2f}ms")
        print(f"最小响应时间: {stats.total.min_response_time:.2f}ms")
        print(f"最大响应时间: {stats.total.max_response_time:.2f}ms")
        print(f"95%响应时间: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        print(f"每秒请求数: {stats.total.current_rps:.2f}")

    print("\n各端点统计:")
    for name in stats.entries.keys():
        if name != "Total":
            entry = stats.entries[name]
            if entry.num_requests > 0:
                print(f"  {name}:")
                print(f"    请求数: {entry.num_requests}")
                print(f"    失败数: {entry.num_failures}")
                print(f"    平均响应时间: {entry.avg_response_time:.2f}ms")
                print(f"    95%响应时间: {entry.get_response_time_percentile(0.95):.2f}ms")

    # 生成HTML报告
    if args.html:
        try:
            import os
            os.makedirs(os.path.dirname(args.html), exist_ok=True)
            with open(args.html, 'w') as f:
                f.write(env.stats.history.to_html())
            print(f"\n📄 HTML报告已生成: {args.html}")
        except Exception as e:
            print(f"生成HTML报告失败: {e}")

    print("\n✅ 测试完成!")


if __name__ == "__main__":
    main()