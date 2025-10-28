#!/usr/bin/env python3
"""
简化压力测试 - 基础API负载测试
专注于核心接口的负载能力测试
"""

import asyncio
import aiohttp
import time
import random
import statistics
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleStressTester:
    """简化压力测试器"""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = []
        self.concurrent_users = 200
        self.test_duration = 60  # 1分钟测试

    async def test_health_endpoint(self, session: aiohttp.ClientSession, user_id: int) -> Dict:
        """测试健康检查接口"""
        start_time = time.time()
        try:
            async with session.get(f"{self.base_url}/health") as response:
                await response.text()
                end_time = time.time()
                return {
                    "user_id": user_id,
                    "operation": "GET /health",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300
                }
        except Exception as e:
            end_time = time.time()
            return {
                "user_id": user_id,
                "operation": "GET /health",
                "response_time": (end_time - start_time) * 1000,
                "status_code": 0,
                "success": False,
                "error": str(e)
            }

    async def test_api_docs_endpoint(self, session: aiohttp.ClientSession, user_id: int) -> Dict:
        """测试API文档接口"""
        start_time = time.time()
        try:
            async with session.get(f"{self.base_url}/docs") as response:
                await response.text()
                end_time = time.time()
                return {
                    "user_id": user_id,
                    "operation": "GET /docs",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300
                }
        except Exception as e:
            end_time = time.time()
            return {
                "user_id": user_id,
                "operation": "GET /docs",
                "response_time": (end_time - start_time) * 1000,
                "status_code": 0,
                "success": False,
                "error": str(e)
            }

    async def test_login_endpoint(self, session: aiohttp.ClientSession, user_id: int) -> Dict:
        """测试登录接口（使用固定账户）"""
        start_time = time.time()
        try:
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            async with session.post(f"{self.base_url}/api/auth/login", json=login_data) as response:
                await response.text()
                end_time = time.time()
                return {
                    "user_id": user_id,
                    "operation": "POST /api/auth/login",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300
                }
        except Exception as e:
            end_time = time.time()
            return {
                "user_id": user_id,
                "operation": "POST /api/auth/login",
                "response_time": (end_time - start_time) * 1000,
                "status_code": 0,
                "success": False,
                "error": str(e)
            }

    async def test_users_endpoint(self, session: aiohttp.ClientSession, user_id: int, token: str = None) -> Dict:
        """测试用户列表接口"""
        start_time = time.time()
        try:
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            async with session.get(f"{self.base_url}/api/admin/users", headers=headers) as response:
                await response.text()
                end_time = time.time()
                return {
                    "user_id": user_id,
                    "operation": "GET /api/admin/users",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300
                }
        except Exception as e:
            end_time = time.time()
            return {
                "user_id": user_id,
                "operation": "GET /api/admin/users",
                "response_time": (end_time - start_time) * 1000,
                "status_code": 0,
                "success": False,
                "error": str(e)
            }

    async def run_user_simulation(self, user_id: int) -> List[Dict]:
        """运行单个用户模拟"""
        operations = []

        # 创建会话
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        connector = aiohttp.TCPConnector(limit=5, limit_per_host=5)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            start_time = time.time()
            token = None

            while time.time() - start_time < self.test_duration:
                try:
                    # 随机选择操作
                    operation_choice = random.random()

                    if operation_choice < 0.3:  # 30% 健康检查
                        op = await self.test_health_endpoint(session, user_id)
                    elif operation_choice < 0.5:  # 20% API文档
                        op = await self.test_api_docs_endpoint(session, user_id)
                    elif operation_choice < 0.8:  # 30% 登录
                        op = await self.test_login_endpoint(session, user_id)
                        # 如果登录成功，保存token
                        if op.get("success") and op.get("status_code") == 200:
                            # 简单的token提取（实际应用中需要解析JSON响应）
                            token = "dummy_token"
                    else:  # 20% 用户列表
                        op = await self.test_users_endpoint(session, user_id, token)

                    operations.append(op)

                    # 随机间隔
                    await asyncio.sleep(random.uniform(0.1, 0.5))

                except Exception as e:
                    logger.error(f"用户 {user_id} 模拟异常: {e}")
                    await asyncio.sleep(0.5)

        return operations

    async def run_stress_test(self):
        """运行压力测试"""
        logger.info(f"开始简化压力测试 - {self.concurrent_users} 并发用户")
        logger.info(f"测试时长: {self.test_duration} 秒")

        start_time = time.time()

        # 创建所有用户任务
        tasks = []
        for user_id in range(1, self.concurrent_users + 1):
            task = asyncio.create_task(self.run_user_simulation(user_id))
            tasks.append(task)

        logger.info(f"启动了 {len(tasks)} 个并发用户任务")

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集所有操作结果
        for i, result in enumerate(results):
            try:
                if isinstance(result, list):
                    self.results.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"任务 {i+1} 异常: {result}")
            except Exception as e:
                logger.error(f"处理任务 {i+1} 结果异常: {e}")

        end_time = time.time()
        duration = end_time - start_time

        logger.info(f"压力测试完成，耗时: {duration:.2f} 秒")

        return self.analyze_results(duration)

    def analyze_results(self, duration: float) -> Dict[str, Any]:
        """分析测试结果"""
        if not self.results:
            return {"error": "没有测试结果可分析"}

        total_operations = len(self.results)
        successful_operations = sum(1 for r in self.results if r.get("success", False))
        failed_operations = total_operations - successful_operations

        # 响应时间统计
        response_times = [r["response_time"] for r in self.results if r.get("success", False)]

        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0
            min_response_time = max_response_time = 0

        # 按操作类型统计
        operation_stats = {}
        for result in self.results:
            operation = result.get("operation", "unknown")
            if operation not in operation_stats:
                operation_stats[operation] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_response_time": 0,
                    "response_times": []
                }

            operation_stats[operation]["total"] += 1
            if result.get("success", False):
                operation_stats[operation]["successful"] += 1
                operation_stats[operation]["response_times"].append(result["response_time"])
            else:
                operation_stats[operation]["failed"] += 1

        # 计算各操作的平均响应时间
        for operation, stats in operation_stats.items():
            if stats["response_times"]:
                stats["avg_response_time"] = statistics.mean(stats["response_times"])
                stats["response_times"] = []  # 清空以减少JSON大小

        # 计算吞吐量
        if duration > 0:
            throughput = total_operations / duration
            success_throughput = successful_operations / duration
        else:
            throughput = success_throughput = 0

        return {
            "test_info": {
                "concurrent_users": self.concurrent_users,
                "test_duration": duration,
                "total_operations": total_operations,
                "start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            "summary": {
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "success_rate": (successful_operations / total_operations * 100) if total_operations > 0 else 0,
                "throughput_ops_per_sec": throughput,
                "success_throughput_ops_per_sec": success_throughput
            },
            "response_time_stats": {
                "average_ms": round(avg_response_time, 2),
                "median_ms": round(median_response_time, 2),
                "p95_ms": round(p95_response_time, 2),
                "p99_ms": round(p99_response_time, 2),
                "min_ms": round(min_response_time, 2),
                "max_ms": round(max_response_time, 2)
            },
            "operation_statistics": operation_stats
        }

    def save_results(self, results: Dict):
        """保存测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        with open(f"simple_stress_test_results_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump({
                "analysis": results,
                "detailed_operations": self.results[:1000]  # 保存前1000条详细操作
            }, f, indent=2, ensure_ascii=False, default=str)

        # 保存简要报告
        with open(f"simple_stress_test_report_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write("MR游戏运营管理系统 - 简化压力测试报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"测试时间: {results['test_info']['start_time']}\n")
            f.write(f"并发用户数: {results['test_info']['concurrent_users']}\n")
            f.write(f"测试时长: {results['test_info']['test_duration']:.2f} 秒\n")
            f.write(f"总操作数: {results['test_info']['total_operations']}\n\n")

            f.write("测试结果摘要:\n")
            f.write(f"  成功操作: {results['summary']['successful_operations']}\n")
            f.write(f"  失败操作: {results['summary']['failed_operations']}\n")
            f.write(f"  成功率: {results['summary']['success_rate']:.2f}%\n")
            f.write(f"  吞吐量: {results['summary']['throughput_ops_per_sec']:.2f} ops/sec\n\n")

            f.write("响应时间统计:\n")
            f.write(f"  平均响应时间: {results['response_time_stats']['average_ms']} ms\n")
            f.write(f"  中位数响应时间: {results['response_time_stats']['median_ms']} ms\n")
            f.write(f"  P95响应时间: {results['response_time_stats']['p95_ms']} ms\n")
            f.write(f"  P99响应时间: {results['response_time_stats']['p99_ms']} ms\n\n")

            f.write("按操作类型统计:\n")
            for operation, stats in results['operation_statistics'].items():
                f.write(f"  {operation}:\n")
                f.write(f"    总数: {stats['total']}, 成功: {stats['successful']}, 失败: {stats['failed']}\n")
                f.write(f"    平均响应时间: {stats['avg_response_time']:.2f} ms\n")

async def main():
    """主函数"""
    # 检查系统是否准备就绪
    logger.info("检查系统状态...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status != 200:
                    logger.error("系统未准备就绪，请先启动应用")
                    return
    except Exception as e:
        logger.error(f"无法连接到系统: {e}")
        return

    # 创建测试器
    tester = SimpleStressTester()

    try:
        # 运行压力测试
        results = await tester.run_stress_test()

        # 打印简要结果
        print("\n" + "=" * 60)
        print("简化压力测试结果")
        print("=" * 60)
        print(f"并发用户数: {results['test_info']['concurrent_users']}")
        print(f"总操作数: {results['test_info']['total_operations']}")
        print(f"成功率: {results['summary']['success_rate']:.2f}%")
        print(f"吞吐量: {results['summary']['throughput_ops_per_sec']:.2f} ops/sec")
        print(f"平均响应时间: {results['response_time_stats']['average_ms']} ms")
        print(f"P95响应时间: {results['response_time_stats']['p95_ms']} ms")

        # 按操作类型显示结果
        print("\n按操作类型统计:")
        for operation, stats in results['operation_statistics'].items():
            success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {operation}: {stats['total']} 次, 成功率 {success_rate:.1f}%, 平均响应时间 {stats['avg_response_time']:.2f} ms")

        # 保存结果
        tester.save_results(results)
        logger.info("测试结果已保存")

    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试执行异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 设置事件循环策略（Windows）
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 运行测试
    asyncio.run(main())