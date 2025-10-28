"""Locust 性能测试 - MR 游戏运营管理系统 (T284)

此测试文件定义了关键 API 端点的性能测试场景。

测试场景:
1. 运营商登录认证
2. 游戏授权验证 (核心功能)
3. 余额查询
4. 运营点查询
5. 支付回调处理

运行方式:
```bash
# Web UI 模式
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# 命令行模式
locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 1m --headless

# 生成 HTML 报告
locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 1m --headless \
    --html=performance_report.html
```

性能目标:
- 游戏授权验证: P95 < 200ms, RPS > 100
- 登录: P95 < 300ms
- 余额查询: P95 < 150ms
"""

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask
import random
import logging

logger = logging.getLogger(__name__)


class OperatorUser(HttpUser):
    """模拟运营商用户行为的性能测试类

    此类模拟运营商的典型操作流程:
    1. 登录获取 token
    2. 执行各种 API 操作 (游戏授权验证是核心)
    3. 定期刷新 token
    """

    # 模拟真实用户的思考时间: 每次操作间隔 1-3 秒
    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.operator_id = None
        self.api_key = None

    def on_start(self):
        """测试用户启动时执行: 登录获取 token

        在实际性能测试中，应该预先创建测试账户。
        这里使用示例账户进行演示。
        """
        # 注意: 在真实测试环境中，需要预先创建大量测试账户
        # 这里使用单一账户仅用于演示
        self.login()

    def login(self):
        """运营商登录"""
        # 使用已存在的测试账户
        login_data = {
            "username": f"test_operator_{random.randint(1, 100)}",
            "password": "Test123!@#"
        }

        with self.client.post(
            "/v1/auth/operators/login",
            json=login_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.operator_id = data.get("operator", {}).get("operator_id")
                response.success()
            elif response.status_code == 401:
                # 账户不存在，尝试注册
                logger.info("Account not found, skipping (use pre-created accounts in real tests)")
                response.failure("Account not found")
                raise RescheduleTask()
            else:
                response.failure(f"Login failed: {response.status_code}")
                raise RescheduleTask()

    def get_headers(self):
        """获取带认证 token 的请求头"""
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    @task(50)  # 权重 50: 游戏授权验证是最频繁的操作
    def game_authorization(self):
        """游戏授权验证 (核心性能测试)

        这是系统最关键的 API，用于验证玩家游戏授权并扣费。
        性能目标: P95 < 200ms, RPS > 100
        """
        if not self.token:
            return

        # 模拟不同的游戏应用
        app_code = random.choice(["GAME_001", "GAME_002", "GAME_003"])

        # 模拟不同的运营点
        site_code = random.choice([f"SITE_{i:03d}" for i in range(1, 11)])

        auth_data = {
            "app_code": app_code,
            "site_code": site_code,
            "player_identifier": f"player_{random.randint(100000, 999999)}",
            "player_count": random.randint(1, 4),  # 1-4 人游戏
            "machine_id": f"MACHINE_{random.randint(1, 50)}"
        }

        with self.client.post(
            "/v1/auth/game/authorize",
            json=auth_data,
            headers=self.get_headers(),
            catch_response=True,
            name="/v1/auth/authorize [核心]"
        ) as response:
            if response.status_code == 200:
                # 检查响应时间
                if response.elapsed.total_seconds() > 0.2:
                    response.failure(f"Response time too slow: {response.elapsed.total_seconds()}s")
                else:
                    response.success()
            elif response.status_code == 402:
                # 余额不足是正常业务场景
                response.success()
            else:
                response.failure(f"Authorization failed: {response.status_code}")

    @task(20)  # 权重 20: 余额查询较频繁
    def get_balance(self):
        """查询运营商余额"""
        if not self.token or not self.operator_id:
            return

        with self.client.get(
            f"/v1/operators/{self.operator_id}/balance",
            headers=self.get_headers(),
            catch_response=True,
            name="/v1/operators/balance"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get balance failed: {response.status_code}")

    @task(15)  # 权重 15: 查询运营点信息
    def get_sites(self):
        """查询运营点列表"""
        if not self.token or not self.operator_id:
            return

        with self.client.get(
            f"/v1/operators/{self.operator_id}/sites",
            headers=self.get_headers(),
            params={"page": 1, "page_size": 10},
            catch_response=True,
            name="/v1/operators/sites"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get sites failed: {response.status_code}")

    @task(10)  # 权重 10: 查询交易记录
    def get_transactions(self):
        """查询交易记录"""
        if not self.token or not self.operator_id:
            return

        with self.client.get(
            f"/v1/operators/{self.operator_id}/transactions",
            headers=self.get_headers(),
            params={"page": 1, "page_size": 20},
            catch_response=True,
            name="/v1/operators/transactions"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get transactions failed: {response.status_code}")

    @task(5)  # 权重 5: 偶尔查询已授权的应用
    def get_authorized_apps(self):
        """查询已授权应用列表"""
        if not self.token or not self.operator_id:
            return

        with self.client.get(
            f"/v1/operators/{self.operator_id}/applications",
            headers=self.get_headers(),
            catch_response=True,
            name="/v1/operators/applications"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get apps failed: {response.status_code}")


class AdminUser(HttpUser):
    """模拟管理员用户行为的性能测试类

    管理员操作频率较低，主要用于测试管理后台性能。
    """

    wait_time = between(3, 8)  # 管理员操作间隔更长

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def on_start(self):
        """管理员登录"""
        self.login()

    def login(self):
        """管理员登录"""
        login_data = {
            "username": "admin_test",
            "password": "Admin123!@#"
        }

        with self.client.post(
            "/v1/admin/login",
            json=login_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            else:
                response.failure(f"Admin login failed: {response.status_code}")
                raise RescheduleTask()

    def get_headers(self):
        """获取带认证 token 的请求头"""
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    @task(30)  # 查询运营商列表
    def get_operators(self):
        """查询运营商列表"""
        if not self.token:
            return

        with self.client.get(
            "/v1/admin/operators",
            headers=self.get_headers(),
            params={"page": 1, "page_size": 20},
            catch_response=True,
            name="/v1/admin/operators"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get operators failed: {response.status_code}")

    @task(20)  # 查询应用列表
    def get_applications(self):
        """查询应用列表"""
        if not self.token:
            return

        with self.client.get(
            "/v1/admin/applications",
            headers=self.get_headers(),
            params={"page": 1, "page_size": 20},
            catch_response=True,
            name="/v1/admin/applications"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get applications failed: {response.status_code}")


# ==================== 性能测试报告钩子 ====================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时的钩子"""
    logger.info("=" * 60)
    logger.info("MR 游戏运营管理系统 - 性能测试开始")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时的钩子"""
    logger.info("=" * 60)
    logger.info("性能测试完成")
    logger.info("=" * 60)

    # 打印性能摘要
    stats = environment.stats
    logger.info("\n性能测试摘要:")
    logger.info(f"总请求数: {stats.total.num_requests}")
    logger.info(f"失败数: {stats.total.num_failures}")
    logger.info(f"平均响应时间: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"P50 响应时间: {stats.total.get_response_time_percentile(0.5):.2f}ms")
    logger.info(f"P95 响应时间: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    logger.info(f"P99 响应时间: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    logger.info(f"RPS (请求/秒): {stats.total.total_rps:.2f}")
