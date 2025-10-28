#!/usr/bin/env python3
"""
高负载压力测试 - 200用户并发测试
测试系统在高压负载下的性能表现
"""

import asyncio
import aiohttp
import time
import random
import statistics
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import psutil
import gc

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('high_load_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HighLoadTester:
    """高负载压力测试器"""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = []
        self.errors = []
        self.concurrent_users = 200
        self.test_duration = 300  # 5分钟测试
        self.ramp_up_time = 60    # 1分钟逐步增加用户
        self.session_cookies = {}
        self.admin_token = None
        self.operator_tokens = []
        self.finance_tokens = []

        # 测试数据
        self.test_users = self._generate_test_users()
        self.test_data = self._generate_test_data()

        # 性能监控
        self.start_time = None
        self.end_time = None
        self.system_metrics = []

    def _generate_test_users(self) -> List[Dict]:
        """生成测试用户"""
        users = []

        # 管理员用户
        users.append({
            "username": "admin",
            "password": "admin123",
            "role": "admin",
            "token": None
        })

        # 运营用户
        for i in range(50):
            users.append({
                "username": f"operator_{i+1:03d}",
                "password": f"op_pass_{i+1:03d}",
                "role": "operator",
                "token": None
            })

        # 财务用户
        for i in range(30):
            users.append({
                "username": f"finance_{i+1:03d}",
                "password": f"fin_pass_{i+1:03d}",
                "role": "finance",
                "token": None
            })

        # 普通用户
        for i in range(119):
            users.append({
                "username": f"user_{i+1:03d}",
                "password": f"user_pass_{i+1:03d}",
                "role": "user",
                "token": None
            })

        return users

    def _generate_test_data(self) -> Dict:
        """生成测试数据"""
        return {
            "sites": [
                {"name": f"Site_{i+1:03d}", "domain": f"site{i+1:03d}.example.com"}
                for i in range(20)
            ],
            "games": [
                {"name": f"Game_{i+1:03d}", "type": random.choice(["slot", "poker", "roulette"])}
                for i in range(50)
            ],
            "transactions": [
                {
                    "user_id": random.randint(1, 200),
                    "amount": round(random.uniform(10, 1000), 2),
                    "type": random.choice(["deposit", "withdraw", "bet", "win"]),
                    "site_id": random.randint(1, 20)
                }
                for _ in range(100)
            ]
        }

    async def login_user(self, session: aiohttp.ClientSession, user: Dict) -> bool:
        """用户登录"""
        try:
            login_data = {
                "username": user["username"],
                "password": user["password"]
            }

            async with session.post(f"{self.base_url}/api/auth/login", json=login_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        user["token"] = data.get("data", {}).get("access_token")
                        return True

                logger.warning(f"用户 {user['username']} 登录失败: {response.status}")
                return False

        except Exception as e:
            logger.error(f"用户 {user['username']} 登录异常: {e}")
            return False

    async def simulate_admin_workload(self, session: aiohttp.ClientSession, user: Dict) -> List[Dict]:
        """模拟管理员工作负载"""
        operations = []

        if not user["token"]:
            if not await self.login_user(session, user):
                return operations

        headers = {"Authorization": f"Bearer {user['token']}"}

        # 管理员操作序列
        admin_operations = [
            # 用户管理
            ("GET", "/api/admin/users", {}),
            ("GET", "/api/admin/users/stats", {}),

            # 系统监控
            ("GET", "/api/admin/system/health", {}),
            ("GET", "/api/admin/system/metrics", {}),

            # 财务概览
            ("GET", "/api/admin/finance/overview", {}),
            ("GET", "/api/admin/finance/transactions", {"limit": 50}),

            # 站点管理
            ("GET", "/api/admin/sites", {}),
            ("POST", "/api/admin/sites", {
                "name": f"Test Site {int(time.time())}",
                "domain": f"test{int(time.time())}.example.com"
            }),

            # 游戏管理
            ("GET", "/api/admin/games", {}),
            ("GET", "/api/admin/games/stats", {}),
        ]

        for method, endpoint, params in admin_operations:
            start_time = time.time()
            try:
                url = f"{self.base_url}{endpoint}"
                if method == "GET":
                    async with session.get(url, headers=headers, params=params) as response:
                        await response.text()
                else:
                    async with session.post(url, headers=headers, json=params) as response:
                        await response.text()

                end_time = time.time()
                operations.append({
                    "user": user["username"],
                    "role": user["role"],
                    "operation": f"{method} {endpoint}",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300
                })

            except Exception as e:
                end_time = time.time()
                operations.append({
                    "user": user["username"],
                    "role": user["role"],
                    "operation": f"{method} {endpoint}",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                })

        return operations

    async def simulate_operator_workload(self, session: aiohttp.ClientSession, user: Dict) -> List[Dict]:
        """模拟运营人员工作负载"""
        operations = []

        if not user["token"]:
            if not await self.login_user(session, user):
                return operations

        headers = {"Authorization": f"Bearer {user['token']}"}

        # 运营人员操作序列
        operator_operations = [
            # 用户查询
            ("GET", "/api/operator/users", {"page": 1, "limit": 20}),
            ("GET", "/api/operator/users/search", {"query": "test"}),

            # 数据统计
            ("GET", "/api/operator/stats/dashboard", {}),
            ("GET", "/api/operator/stats/users", {}),
            ("GET", "/api/operator/stats/revenue", {"days": 7}),

            # 站点管理
            ("GET", "/api/operator/sites", {}),
            ("PUT", f"/api/operator/sites/{random.randint(1, 20)}", {
                "name": f"Updated Site {int(time.time())}"
            }),

            # 游戏管理
            ("GET", "/api/operator/games", {}),
            ("POST", "/api/operator/games", {
                "name": f"Test Game {int(time.time())}",
                "type": random.choice(["slot", "poker", "roulette"])
            }),
        ]

        for method, endpoint, params in operator_operations:
            start_time = time.time()
            try:
                url = f"{self.base_url}{endpoint}"
                if method == "GET":
                    async with session.get(url, headers=headers, params=params) as response:
                        await response.text()
                elif method == "PUT":
                    async with session.put(url, headers=headers, json=params) as response:
                        await response.text()
                else:
                    async with session.post(url, headers=headers, json=params) as response:
                        await response.text()

                end_time = time.time()
                operations.append({
                    "user": user["username"],
                    "role": user["role"],
                    "operation": f"{method} {endpoint}",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300
                })

            except Exception as e:
                end_time = time.time()
                operations.append({
                    "user": user["username"],
                    "role": user["role"],
                    "operation": f"{method} {endpoint}",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                })

        return operations

    async def simulate_finance_workload(self, session: aiohttp.ClientSession, user: Dict) -> List[Dict]:
        """模拟财务人员工作负载"""
        operations = []

        if not user["token"]:
            if not await self.login_user(session, user):
                return operations

        headers = {"Authorization": f"Bearer {user['token']}"}

        # 财务人员操作序列
        finance_operations = [
            # 交易查询
            ("GET", "/api/finance/transactions", {"page": 1, "limit": 50}),
            ("GET", "/api/finance/transactions/search", {
                "user_id": random.randint(1, 200),
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }),

            # 财务报表
            ("GET", "/api/finance/reports/daily", {"date": "2024-01-01"}),
            ("GET", "/api/finance/reports/monthly", {"month": "2024-01"}),
            ("GET", "/api/finance/reports/yearly", {"year": "2024"}),

            # 余额管理
            ("GET", "/api/finance/balances", {}),
            ("POST", "/api/finance/balances/adjust", {
                "user_id": random.randint(1, 200),
                "amount": round(random.uniform(10, 1000), 2),
                "type": "deposit",
                "note": f"Test adjustment {int(time.time())}"
            }),

            # 提现审核
            ("GET", "/api/finance/withdrawals", {"status": "pending"}),
            ("PUT", f"/api/finance/withdrawals/{random.randint(1, 100)}/approve", {
                "status": "approved",
                "note": "Approved in stress test"
            }),
        ]

        for method, endpoint, params in finance_operations:
            start_time = time.time()
            try:
                url = f"{self.base_url}{endpoint}"
                if method == "GET":
                    async with session.get(url, headers=headers, params=params) as response:
                        await response.text()
                elif method == "PUT":
                    async with session.put(url, headers=headers, json=params) as response:
                        await response.text()
                else:
                    async with session.post(url, headers=headers, json=params) as response:
                        await response.text()

                end_time = time.time()
                operations.append({
                    "user": user["username"],
                    "role": user["role"],
                    "operation": f"{method} {endpoint}",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300
                })

            except Exception as e:
                end_time = time.time()
                operations.append({
                    "user": user["username"],
                    "role": user["role"],
                    "operation": f"{method} {endpoint}",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                })

        return operations

    async def simulate_user_workload(self, session: aiohttp.ClientSession, user: Dict) -> List[Dict]:
        """模拟普通用户工作负载"""
        operations = []

        if not user["token"]:
            if not await self.login_user(session, user):
                return operations

        headers = {"Authorization": f"Bearer {user['token']}"}

        # 普通用户操作序列
        user_operations = [
            # 个人信息
            ("GET", "/api/user/profile", {}),
            ("PUT", "/api/user/profile", {
                "nickname": f"User_{int(time.time())}",
                "avatar": "https://example.com/avatar.jpg"
            }),

            # 余额查询
            ("GET", "/api/user/balance", {}),
            ("GET", "/api/user/transactions", {"limit": 20}),

            # 游戏操作
            ("GET", "/api/user/games", {}),
            ("POST", "/api/user/games/play", {
                "game_id": random.randint(1, 50),
                "bet_amount": round(random.uniform(1, 100), 2)
            }),

            # 充值提现
            ("POST", "/api/user/deposit", {
                "amount": round(random.uniform(10, 500), 2),
                "method": "credit_card"
            }),
            ("POST", "/api/user/withdraw", {
                "amount": round(random.uniform(10, 200), 2),
                "method": "bank_transfer"
            }),
        ]

        for method, endpoint, params in user_operations:
            start_time = time.time()
            try:
                url = f"{self.base_url}{endpoint}"
                if method == "GET":
                    async with session.get(url, headers=headers, params=params) as response:
                        await response.text()
                else:
                    async with session.post(url, headers=headers, json=params) as response:
                        await response.text()

                end_time = time.time()
                operations.append({
                    "user": user["username"],
                    "role": user["role"],
                    "operation": f"{method} {endpoint}",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300
                })

            except Exception as e:
                end_time = time.time()
                operations.append({
                    "user": user["username"],
                    "role": user["role"],
                    "operation": f"{method} {endpoint}",
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                })

        return operations

    async def run_user_simulation(self, user: Dict, duration: int) -> List[Dict]:
        """运行单个用户模拟"""
        operations = []

        # 创建会话
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=10)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # 用户登录
            if not await self.login_user(session, user):
                logger.error(f"用户 {user['username']} 登录失败，跳过测试")
                return operations

            start_time = time.time()

            # 根据用户角色选择不同的工作负载
            while time.time() - start_time < duration:
                try:
                    if user["role"] == "admin":
                        user_ops = await self.simulate_admin_workload(session, user)
                    elif user["role"] == "operator":
                        user_ops = await self.simulate_operator_workload(session, user)
                    elif user["role"] == "finance":
                        user_ops = await self.simulate_finance_workload(session, user)
                    else:
                        user_ops = await self.simulate_user_workload(session, user)

                    operations.extend(user_ops)

                    # 随机间隔（模拟真实用户行为）
                    await asyncio.sleep(random.uniform(0.5, 2.0))

                except Exception as e:
                    logger.error(f"用户 {user['username']} 模拟异常: {e}")
                    await asyncio.sleep(1)  # 出错后短暂休息

        return operations

    async def monitor_system_metrics(self):
        """监控系统性能指标"""
        while self.start_time and (time.time() - self.start_time) < self.test_duration:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)

                # 内存使用情况
                memory = psutil.virtual_memory()

                # 磁盘使用情况
                disk = psutil.disk_usage('/')

                # 网络统计
                network = psutil.net_io_counters()

                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_gb": memory.used / (1024**3),
                    "memory_total_gb": memory.total / (1024**3),
                    "disk_percent": (disk.used / disk.total) * 100,
                    "network_bytes_sent": network.bytes_sent,
                    "network_bytes_recv": network.bytes_recv,
                    "active_connections": len(asyncio.all_tasks())
                }

                self.system_metrics.append(metrics)

                # 每30秒记录一次
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"监控系统指标异常: {e}")
                await asyncio.sleep(30)

    async def run_high_load_test(self):
        """运行高负载测试"""
        logger.info(f"开始高负载测试 - {self.concurrent_users} 并发用户")
        logger.info(f"测试时长: {self.test_duration} 秒")
        logger.info(f"逐步增加用户时间: {self.ramp_up_time} 秒")

        self.start_time = time.time()

        # 启动系统监控
        monitor_task = asyncio.create_task(self.monitor_system_metrics())

        try:
            # 逐步增加用户
            users_per_ramp = self.concurrent_users // (self.ramp_up_time // 10)
            current_users = 0

            # 创建任务列表
            tasks = []

            while current_users < len(self.test_users) and current_users < self.concurrent_users:
                # 每隔10秒增加一批用户
                batch_size = min(users_per_ramp, self.concurrent_users - current_users)
                batch_users = self.test_users[current_users:current_users + batch_size]

                logger.info(f"启动第 {current_users + 1}-{current_users + batch_size} 个用户")

                # 为这批用户创建任务
                for user in batch_users:
                    remaining_time = max(0, self.test_duration - (time.time() - self.start_time))
                    if remaining_time > 0:
                        task = asyncio.create_task(self.run_user_simulation(user, remaining_time))
                        tasks.append(task)

                current_users += batch_size

                # 等待10秒再增加下一批用户
                if current_users < self.concurrent_users:
                    await asyncio.sleep(10)

            logger.info(f"所有 {current_users} 个用户已启动，等待测试完成...")

            # 等待所有任务完成
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            self.end_time = time.time()

            # 收集所有操作结果
            for task in tasks:
                try:
                    if task.done():
                        result = task.result()
                        if isinstance(result, list):
                            self.results.extend(result)
                except Exception as e:
                    logger.error(f"任务执行异常: {e}")

            logger.info("高负载测试完成")

        finally:
            # 停止监控
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

    def analyze_results(self) -> Dict[str, Any]:
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
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0
            min_response_time = max_response_time = 0

        # 按角色统计
        role_stats = {}
        for result in self.results:
            role = result.get("role", "unknown")
            if role not in role_stats:
                role_stats[role] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_response_time": 0,
                    "response_times": []
                }

            role_stats[role]["total"] += 1
            if result.get("success", False):
                role_stats[role]["successful"] += 1
                role_stats[role]["response_times"].append(result["response_time"])
            else:
                role_stats[role]["failed"] += 1

        # 计算各角色的平均响应时间
        for role, stats in role_stats.items():
            if stats["response_times"]:
                stats["avg_response_time"] = statistics.mean(stats["response_times"])
                stats["response_times"] = []  # 清空以减少JSON大小

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

        # 错误统计
        error_stats = {}
        for result in self.results:
            if not result.get("success", False) and "error" in result:
                error = result["error"]
                error_stats[error] = error_stats.get(error, 0) + 1

        # 计算吞吐量
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            throughput = total_operations / duration
            success_throughput = successful_operations / duration
        else:
            duration = throughput = success_throughput = 0

        # 系统资源使用统计
        if self.system_metrics:
            avg_cpu = statistics.mean([m["cpu_percent"] for m in self.system_metrics])
            max_cpu = max([m["cpu_percent"] for m in self.system_metrics])
            avg_memory = statistics.mean([m["memory_percent"] for m in self.system_metrics])
            max_memory = max([m["memory_percent"] for m in self.system_metrics])
        else:
            avg_cpu = max_cpu = avg_memory = max_memory = 0

        return {
            "test_info": {
                "concurrent_users": self.concurrent_users,
                "test_duration": duration,
                "total_operations": total_operations,
                "start_time": self.start_time,
                "end_time": self.end_time
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
            "role_statistics": role_stats,
            "operation_statistics": operation_stats,
            "error_statistics": error_stats,
            "system_performance": {
                "avg_cpu_percent": round(avg_cpu, 2),
                "max_cpu_percent": round(max_cpu, 2),
                "avg_memory_percent": round(avg_memory, 2),
                "max_memory_percent": round(max_memory, 2),
                "metrics_count": len(self.system_metrics)
            }
        }

    def save_results(self, results: Dict):
        """保存测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        with open(f"high_load_test_results_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump({
                "analysis": results,
                "detailed_operations": self.results[:1000],  # 保存前1000条详细操作
                "system_metrics": self.system_metrics
            }, f, indent=2, ensure_ascii=False, default=str)

        # 保存简要报告
        with open(f"high_load_test_report_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write("MR游戏运营管理系统 - 高负载压力测试报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"并发用户数: {results['test_info']['concurrent_users']}\n")
            f.write(f"测试时长: {results['test_info']['test_duration']:.2f} 秒\n")
            f.write(f"总操作数: {results['summary']['total_operations']}\n\n")

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

            f.write("系统性能:\n")
            f.write(f"  平均CPU使用率: {results['system_performance']['avg_cpu_percent']}%\n")
            f.write(f"  最大CPU使用率: {results['system_performance']['max_cpu_percent']}%\n")
            f.write(f"  平均内存使用率: {results['system_performance']['avg_memory_percent']}%\n")
            f.write(f"  最大内存使用率: {results['system_performance']['max_memory_percent']}%\n\n")

            if results['error_statistics']:
                f.write("主要错误:\n")
                for error, count in list(results['error_statistics'].items())[:10]:
                    f.write(f"  {error}: {count} 次\n")

async def main():
    """主函数"""
    # 检查系统是否准备就绪
    logger.info("检查系统状态...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status != 200:
                    logger.error("系统未准备就绪，请先启动应用")
                    return
    except Exception as e:
        logger.error(f"无法连接到系统: {e}")
        return

    # 创建测试器
    tester = HighLoadTester()

    try:
        # 运行高负载测试
        await tester.run_high_load_test()

        # 分析结果
        logger.info("分析测试结果...")
        results = tester.analyze_results()

        # 打印简要结果
        print("\n" + "=" * 60)
        print("高负载压力测试结果")
        print("=" * 60)
        print(f"并发用户数: {results['test_info']['concurrent_users']}")
        print(f"总操作数: {results['summary']['total_operations']}")
        print(f"成功率: {results['summary']['success_rate']:.2f}%")
        print(f"吞吐量: {results['summary']['throughput_ops_per_sec']:.2f} ops/sec")
        print(f"平均响应时间: {results['response_time_stats']['average_ms']} ms")
        print(f"P95响应时间: {results['response_time_stats']['p95_ms']} ms")
        print(f"最大CPU使用率: {results['system_performance']['max_cpu_percent']}%")
        print(f"最大内存使用率: {results['system_performance']['max_memory_percent']}%")

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