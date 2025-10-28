"""负载压力测试

测试系统在高并发下的表现和稳定性。
"""

import asyncio
import time
import pytest
import signal
import sys
from httpx import AsyncClient, Limits, PoolLimits
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from src.main import app
from tests.conftest import reset_database, create_test_applications


@dataclass
class LoadTestMetrics:
    """负载测试指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    errors: List[str] = []

    def add_request(self, duration: float, success: bool, error: str = None):
        """添加请求结果"""
        self.total_requests += 1
        self.total_response_time += duration

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)

        self.min_response_time = min(self.min_response_time, duration)
        self.max_response_time = max(self.max_response_time, duration)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "avg_response_time": self.total_response_time / self.total_requests if self.total_requests > 0 else 0,
            "min_response_time": self.min_response_time,
            "max_response_time": self.max_response_time,
            "requests_per_second": self.total_requests / (self.total_response_time or 1)
        }


class LoadTester:
    """负载测试器"""

    def __init__(self, base_url: str = "http://test"):
        self.base_url = base_url
        self.client_limits = Limits(
            max_keepalive_connections=100,
            max_connections=100,
            keepalive_expiry=30
        )
        self.metrics = LoadTestMetrics()
        self.running = False

    async def single_request(self, endpoint: str, method: str = "GET",
                           json_data: Dict = None, headers: Dict = None) -> bool:
        """单个请求测试"""
        try:
            async with AsyncClient(limits=self.client_limits, base_url=self.base_url) as client:
                start_time = time.time()

                if method == "GET":
                    response = await client.get(endpoint, headers=headers)
                elif method == "POST":
                    response = await client.post(endpoint, json=json_data, headers=headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                end_time = time.time()
                duration = end_time - start_time

                success = 200 <= response.status_code < 300
                error = f"HTTP {response.status_code}" if not success else None

                self.metrics.add_request(duration, success, error)
                return success

        except Exception as e:
            self.metrics.add_request(0, False, str(e))
            return False

    async def warmup(self, endpoint: str, count: int = 10):
        """预热连接池"""
        print(f"🔥 预热 {count} 个连接到 {endpoint}")
        for i in range(count):
            await self.single_request(endpoint)
            if (i + 1) % 10 == 0:
                print(f"  预热进度: {i + 1}/{count}")

    async def sustained_load(self, endpoint: str, duration: int, rps: int,
                         method: str = "GET", json_data: Dict = None, headers: Dict = None):
        """持续负载测试"""
        print(f"🚀 开始持续负载测试")
        print(f"   端点: {endpoint}")
        print(f"   持续时间: {duration}秒")
        print(f"   目标RPS: {rps}")
        print(f"   请求方法: {method}")

        interval = 1.0 / rps  # 请求间隔
        start_time = time.time()
        end_time = start_time + duration

        request_count = 0

        while time.time() < end_time and self.running:
            start_request_time = time.time()

            # 计算下一个请求时间
            next_request_time = start_time + interval * (request_count + 1)

            # 执行请求
            await self.single_request(endpoint, method, json_data, headers)
            request_count += 1

            # 如果还有时间，等待到下一个请求时间
            if time.time() < end_time:
                sleep_time = next_request_time - time.time()
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        actual_duration = time.time() - start_time
        actual_rps = request_count / actual_duration

        print(f"✅ 持续负载测试完成")
        print(f"   实际持续时间: {actual_duration:.2f}s")
        print(f"   实际RPS: {actual_rps:.2f}")
        print(f"   总请求数: {request_count}")

    async def burst_load(self, endpoint: str, total_requests: int,
                      concurrency: int = 10, method: str = "GET",
                      json_data: Dict = None, headers: Dict = None):
        """突发负载测试"""
        print(f"💥 开始突发负载测试")
        print(f"   端点: {endpoint}")
        print(f"   总请求数: {total_requests}")
        print(f"   并发数: {concurrency}")
        print(f"   请求方法: {method}")

        async def burst_batch(batch_size: int, batch_requests: int):
            """执行一批突发请求"""
            tasks = []
            for _ in range(batch_requests):
                task = self.single_request(endpoint, method, json_data, headers)
                tasks.append(task)

            await asyncio.gather(*tasks)

        # 分批执行突发请求
        batch_size = concurrency
        remaining_requests = total_requests
        completed_requests = 0

        while remaining_requests > 0 and self.running:
            current_batch_size = min(batch_size, remaining_requests)

            batch_start_time = time.time()
            await burst_batch(batch_size, current_batch_size)
            batch_end_time = time.time()

            batch_duration = batch_end_time - batch_start_time
            completed_requests += current_batch_size
            remaining_requests -= current_batch_size

            print(f"   批次 {current_batch_size} 请求，耗时 {batch_duration:.3f}s，"
                  f"已完成 {completed_requests}/{total_requests}")

        print(f"✅ 突发负载测试完成")

    def stop(self):
        """停止测试"""
        self.running = False


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.slow
class TestLoadStress:

    @pytest.fixture
    async def load_tester(self):
        """负载测试器实例"""
        return LoadTester()

    async def test_admin_login_load(self, load_tester, test_db):
        """管理员登录负载测试"""
        await reset_database(test_db)

        # 预热
        await load_tester.warmup("/v1/admin/login", 10)

        # 持续负载测试 - 50 RPS，持续30秒
        await load_tester.sustained_load(
            "/v1/admin/login",
            duration=30,
            rps=50,
            method="POST",
            json_data={"username": "admin", "password": "Admin123"}
        )

        # 验证结果
        stats = load_tester.metrics.get_stats()
        assert stats["success_rate"] >= 0.95, f"成功率过低: {stats['success_rate']:.2%}"
        assert stats["avg_response_time"] <= 1.0, f"平均响应时间过长: {stats['avg_response_time']:.3f}s"

    async def test_operator_authorization_load(self, load_tester, test_db):
        """运营商授权负载测试"""
        await reset_database(test_db)
        await create_test_applications(test_db)

        # 创建测试运营商
        register_data = {
            "username": "load_operator",
            "password": "Load@2025",
            "name": "负载测试运营商",
            "email": "load@test.com",
            "phone": "13800138000",
            "company_name": "负载测试公司"
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            reg_response = await client.post("/v1/auth/operators/register", json=register_data)
            assert reg_response.status_code == 201

            login_response = await client.post("/v1/auth/operators/login", json={
                "username": "load_operator",
                "password": "Load@2025"
            })
            assert login_response.status_code == 200

            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 预热
            await load_tester.warmup("/v1/games/authorize", 5, headers=headers)

            # 持续负载测试 - 20 RPS，持续60秒
            await load_tester.sustained_load(
                "/v1/games/authorize",
                duration=60,
                rps=20,
                method="POST",
                json_data={
                    "app_id": 1,
                    "player_count": 5,
                    "session_id": "load_test_session"
                },
                headers=headers
            )

            # 验证结果
            stats = load_tester.metrics.get_stats()
            assert stats["success_rate"] >= 0.95, f"成功率过低: {stats['success_rate']:.2%}"
            assert stats["avg_response_time"] <= 0.5, f"平均响应时间过长: {stats['avg_response_time']:.3f}s"

    async def test_balance_query_load(self, load_tester, test_db):
        """余额查询负载测试"""
        await reset_database(test_db)
        await create_test_applications(test_db)

        # 创建测试运营商
        register_data = {
            "username": "balance_load_operator",
            "password": "Balance@2025",
            "name": "余额负载测试",
            "email": "balance@test.com",
            "phone": "13800138001"
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            reg_response = await client.post("/v1/auth/operators/register", json=register_data)
            assert reg_response.status_code == 201

            login_response = await client.post("/v1/auth/operators/login", json={
                "username": "balance_load_operator",
                "password": "Balance@2025"
            })
            assert login_response.status_code == 200

            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 预热
            await load_tester.warmup("/v1/balance", 10, headers=headers)

            # 持续负载测试 - 100 RPS，持续30秒
            await load_tester.sustained_load(
                "/v1/balance",
                duration=30,
                rps=100,
                headers=headers
            )

            # 验证结果
            stats = load_tester.metrics.get_stats()
            assert stats["success_rate"] >= 0.98, f"成功率过低: {stats['success_rate']:.2%}"
            assert stats["avg_response_time"] <= 0.2, f"平均响应时间过长: {stats['avg_response_time']:.3f}s"

    async def test_mixed_workload(self, load_tester, test_db):
        """混合工作负载测试"""
        await reset_database(test_db)
        await create_test_applications(test_db)

        # 创建多个运营商账户
        operators = []
        for i in range(3):
            register_data = {
                "username": f"mixed_operator_{i}",
                "password": f"Mixed@2025{i}",
                "name": f"混合测试运营商{i}",
                "email": f"mixed{i}@test.com",
                "phone": f"1380013800{i}"
            }

            async with AsyncClient(app=app, base_url="http://test") as client:
                reg_response = await client.post("/v1/auth/operators/register", json=register_data)
                assert reg_response.status_code == 201

                login_response = await client.post("/v1/auth/operators/login", json={
                    "username": f"mixed_operator_{i}",
                    "password": f"Mixed@2025{i}"
                })
                assert login_response.status_code == 200

                operators.append({
                    "token": login_response.json()["access_token"],
                    "headers": {"Authorization": f"Bearer {login_response.json()['access_token']}"}
                })

        print(f"✅ 创建了 {len(operators)} 个运营商账户")

        # 混合负载测试 - 不同类型的请求
        await load_tester.warmup("/v1/admin/login", 5)
        await load_tester.warmup("/v1/balance", 5, headers=operators[0]["headers"])

        async def mixed_requests():
            """混合请求函数"""
            while load_tester.running:
                # 管理员登录 (低频)
                if time.time() % 10 == 0:  # 每10秒一次
                    await load_tester.single_request("/v1/admin/login", "POST",
                                                       {"username": "admin", "password": "Admin123"})

                # 余额查询 (高频)
                await load_tester.single_request("/v1/balance", headers=operators[0]["headers"])

                # 休息一下
                await asyncio.sleep(0.1)

        # 运行混合负载测试60秒
        load_tester.running = True
        await asyncio.wait_for(mixed_requests(), timeout=65)

    async def test_ramp_up_load(self, load_tester, test_db):
        """递增负载测试"""
        await reset_database(test_db)
        await create_test_applications(test_db)

        # 创建测试运营商
        register_data = {
            "username": "ramp_up_operator",
            "password": "RampUp@2025",
            "name": "递增负载测试",
            "email": "ramp@test.com",
            "phone": "13800138000"
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            reg_response = await client.post("/v1/auth/operators/register", json=register_data)
            assert reg_response.status_code == 201

            login_response = await client.post("/v1/auth/operators/login", json={
                "username": "ramp_up_operator",
                "password": "RampUp@2025"
            })
            assert login_response.status_code == 200

            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 预热
            await load_tester.warmup("/v1/balance", 5, headers=headers)

            print(f"📈 开始递增负载测试 (10-100 RPS)")

            # 递增RPS: 10 -> 100，每10秒增加10 RPS
            for rps in range(10, 101, 10):
                print(f"   测试 {rps} RPS 持续10秒...")

                await load_tester.sustained_load(
                    "/v1/balance",
                    duration=10,
                    rps=rps,
                    headers=headers
                )

                stats = load_tester.metrics.get_stats()
                print(f"     当前RPS: {rps}, 成功率: {stats['success_rate']:.2%}, "
                      f"平均响应时间: {stats['avg_response_time']:.3f}s")

    def test_load_stress_summary(self, load_tester):
        """负载测试总结"""
        load_tester.stop()
        load_tester.metrics.print_summary()


if __name__main__":
    # 处理Ctrl+C信号
    def signal_handler(signum, frame):
        print("\n🛑 收到中断信号，正在停止测试...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    pytest.main([__file__, "-v", "-s"])