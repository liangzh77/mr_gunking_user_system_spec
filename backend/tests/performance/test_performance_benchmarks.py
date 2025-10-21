"""性能基准测试

测试系统在各种负载下的性能表现。
"""

import asyncio
import time
import pytest
import statistics
from decimal import Decimal
from httpx import AsyncClient
from typing import List, Dict, Any

from src.main import app
from tests.conftest import (
    reset_database,
    create_test_applications,
    get_test_admin_token,
    get_test_finance_token
)


class PerformanceBenchmark:
    """性能基准测试类"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def record_result(self, test_name: str, duration: float, success: bool, **kwargs):
        """记录测试结果"""
        self.results.append({
            "test_name": test_name,
            "duration": duration,
            "success": success,
            "timestamp": time.time(),
            **kwargs
        })

    def get_statistics(self, test_name: str) -> Dict[str, float]:
        """获取特定测试的统计信息"""
        test_results = [r for r in self.results if r["test_name"] == test_name and r["success"]]

        if not test_results:
            return {}

        durations = [r["duration"] for r in test_results]
        return {
            "count": len(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": statistics.mean(durations),
            "median": statistics.median(durations),
            "p95": statistics.quantiles(durations, 0.95),
            "p99": statistics.quantiles(durations, 0.99),
        }

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*80)
        print("📊 性能基准测试总结")
        print("="*80)

        test_names = list(set(r["test_name"] for r in self.results))

        for test_name in sorted(test_names):
            stats = self.get_statistics(test_name)
            if stats:
                print(f"\n🧪 {test_name}")
                print(f"   测试次数: {stats['count']}")
                print(f"   平均响应时间: {stats['avg']:.3f}s")
                print(f"   P95响应时间: {stats['p95']:.3f}s")
                print(f"   P99响应时间: {stats['p99']:.3f}s")
                print(f"   最小响应时间: {stats['min']:.3f}s")
                print(f"   最大响应时间: {stats['max']:.3f}s")

        # 总体统计
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r["success"]])
        success_rate = successful_tests / total_tests if total_tests > 0 else 0

        print(f"\n📈 总体统计")
        print(f"   总测试数: {total_tests}")
        print(f"   成功测试数: {successful_tests}")
        print(f"   成功率: {success_rate:.2%}")

        if success_rate < 0.95:
            print(f"⚠️  警告: 成功率低于95%")
        else:
            print(f"✅ 成功率良好")

        print("="*80)


@pytest.mark.asyncio
@pytest.mark.performance
class TestPerformanceBenchmarks:

    @pytest.fixture
    async def benchmark(self):
        """性能基准测试实例"""
        return PerformanceBenchmark()

    async def test_admin_login_performance(self, benchmark, test_db):
        """测试管理员登录性能"""

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 重置数据库
            await reset_database(test_db)

            login_data = {
                "username": "admin",
                "password": "Admin123"
            }

            # 预热
            for _ in range(5):
                await client.post("/v1/admin/login", json=login_data)

            # 正式测试
            for i in range(20):
                start_time = time.time()

                response = await client.post("/v1/admin/login", json=login_data)

                end_time = time.time()
                duration = end_time - start_time

                benchmark.record_result(
                    "admin_login",
                    duration,
                    response.status_code == 200,
                    iteration=i + 1
                )

    async def test_operator_authorization_performance(self, benchmark, test_db):
        """测试运营商游戏授权性能"""

        async with AsyncClient(app=app, base_url="http://test") as client:

            # 准备测试数据
            await reset_database(test_db)
            await create_test_applications(test_db)

            # 创建测试运营商
            register_data = {
                "username": "perf_test_operator",
                "password": "Perf@2025",
                "name": "性能测试运营商",
                "email": "perf@test.com",
                "phone": "13800138000",
                "company_name": "性能测试公司"
            }

            reg_response = await client.post("/v1/auth/operators/register", json=register_data)
            assert reg_response.status_code == 201

            # 登录获取token
            login_response = await client.post("/v1/auth/operators/login", json={
                "username": "perf_test_operator",
                "password": "Perf@2025"
            })
            assert login_response.status_code == 200

            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 预热
            for _ in range(5):
                await client.post(
                    "/v1/games/authorize",
                    json={
                        "app_id": 1,
                        "player_count": 5,
                        "session_id": f"warmup_{int(time.time())}"
                    },
                    headers=headers
                )

            # 正式测试
            for i in range(50):
                start_time = time.time()

                response = await client.post(
                    "/v1/games/authorize",
                    json={
                        "app_id": 1,
                        "player_count": 5,
                        "session_id": f"perf_test_{i}_{int(time.time())}"
                    },
                    headers=headers
                )

                end_time = time.time()
                duration = end_time - start_time

                benchmark.record_result(
                    "operator_authorization",
                    duration,
                    response.status_code == 200,
                    iteration=i + 1
                )

    async def test_balance_query_performance(self, benchmark, test_db):
        """测试余额查询性能"""

        async with AsyncClient(app=app, base_url="http://test") as client:

            # 准备测试数据
            await reset_database(test_db)
            await create_test_applications(test_db)

            # 创建测试运营商
            register_data = {
                "username": "balance_perf_operator",
                "password": "Perf@2025",
                "name": "余额性能测试",
                "email": "balance@test.com",
                "phone": "13800138001"
            }

            reg_response = await client.post("/v1/auth/operators/register", json=register_data)
            assert reg_response.status_code == 201

            # 登录获取token
            login_response = await client.post("/v1/auth/operators/login", json={
                "username": "balance_perf_operator",
                "password": "Perf@2025"
            })
            assert login_response.status_code == 200

            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 性能测试
            for i in range(100):
                start_time = time.time()

                response = await client.get("/v1/balance", headers=headers)

                end_time = time.time()
                duration = end_time - start_time

                benchmark.record_result(
                    "balance_query",
                    duration,
                    response.status_code == 200,
                    iteration=i + 1
                )

    async def test_transaction_query_performance(self, benchmark, test_db):
        """测试交易记录查询性能"""

        async with AsyncClient(app=app, base_url="http://test") as client:

            # 准备测试数据
            await reset_database(test_db)
            await create_test_applications(test_db)

            # 创建测试运营商
            register_data = {
                "username": "tx_perf_operator",
                "password": "Perf@2025",
                "name": "交易性能测试",
                "email": "tx@test.com",
                "phone": "13800138002"
            }

            reg_response = await client.post("/v1/auth/operators/register", json=register_data)
            assert reg_response.status_code == 201

            # 登录获取token
            login_response = await client.post("/v1/auth/operators/login", json={
                "username": "tx_perf_operator",
                "password": "Perf@2025"
            })
            assert login_response.status_code == 200

            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 性能测试 - 不同页大小的查询
            page_sizes = [10, 20, 50, 100]

            for page_size in page_sizes:
                for i in range(10):  # 每个页大小测试10次
                    start_time = time.time()

                    response = await client.get(
                        "/v1/transactions",
                        headers=headers,
                        params={"page_size": page_size}
                    )

                    end_time = time.time()
                    duration = end_time - start_time

                    benchmark.record_result(
                        f"transaction_query_page_{page_size}",
                        duration,
                        response.status_code == 200,
                        page_size=page_size,
                        iteration=i + 1
                    )

    async def test_concurrent_operations(self, benchmark, test_db):
        """测试并发操作性能"""

        async with AsyncClient(app=app, base_url="http://test") as client:

            # 准备测试数据
            await reset_database(test_db)
            await create_test_applications(test_db)

            # 创建多个运营商账户
            operators = []
            for i in range(5):
                register_data = {
                    "username": f"concurrent_operator_{i}",
                    "password": f"Concurrent@2025{i}",
                    "name": f"并发测试运营商{i}",
                    "email": f"concurrent{i}@test.com",
                    "phone": f"1380013800{i}"
                }

                reg_response = await client.post("/v1/auth/operators/register", json=register_data)
                assert reg_response.status_code == 201

                # 登录获取token
                login_response = await client.post("/v1/auth/operators/login", json={
                    "username": f"concurrent_operator_{i}",
                    "password": f"Concurrent@2025{i}"
                })
                assert login_response.status_code == 200

                operators.append({
                    "token": login_response.json()["access_token"],
                    "operator_id": reg_response.json()["operator_id"]
                })

            print(f"✅ 创建了 {len(operators)} 个运营商账户")

            # 并发余额查询测试
            async def query_balance(operator_data, operator_index):
                headers = {"Authorization": f"Bearer {operator_data['token']}"}

                start_time = time.time()
                response = await client.get("/v1/balance", headers=headers)
                end_time = time.time()

                return {
                    "operator_index": operator_index,
                    "duration": end_time - start_time,
                    "success": response.status_code == 200
                }

            # 执行并发查询
            start_time = time.time()
            balance_tasks = [
                query_balance(operator, i)
                for i, operator in enumerate(operators)
            ]

            balance_results = await asyncio.gather(*balance_tasks)
            end_time = time.time()

            # 统计结果
            successful_queries = sum(1 for r in balance_results if r["success"])
            total_duration = end_time - start_time
            avg_duration = sum(r["duration"] for r in balance_results) / len(balance_results)

            benchmark.record_result(
                "concurrent_balance_queries",
                total_duration,
                successful_queries == len(operators),
                total_requests=len(operators),
                successful_requests=successful_queries,
                avg_duration=avg_duration
            )

            print(f"✅ 并发余额查询完成")
            print(f"   总请求数: {len(operators)}")
            print(f"   成功请求数: {successful_queries}")
            print(f"   总耗时: {total_duration:.3f}s")
            print(f"   平均耗时: {avg_duration:.3f}s")

    def test_performance_summary(self, benchmark):
        """测试性能总结"""
        benchmark.print_summary()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])