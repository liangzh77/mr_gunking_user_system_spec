#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
头显Server API 性能测试脚本

测试3个核心接口的响应时间和成功率:
1. 预授权查询 (POST /api/v1/auth/game/pre-authorize)
2. 游戏授权 (POST /api/v1/auth/game/authorize)
3. 上传游戏会话数据 (POST /api/v1/auth/game/session/upload)
"""

import sys
import io
import os
import argparse
import requests
import json
import time
import urllib3
from datetime import datetime
from typing import Dict, Any, List, Optional

# 禁用 HTTPS 警告 (用于开发服务器)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Fix Windows console encoding and enable ANSI colors
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    # Enable ANSI escape sequences in Windows 10+
    os.system('')  # This enables ANSI escape codes in Windows console


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


class TestResult:
    """单次测试结果"""
    def __init__(self, success: bool, duration_ms: float, error_msg: str = ""):
        self.success = success
        self.duration_ms = duration_ms
        self.error_msg = error_msg


class APITestStats:
    """API测试统计"""
    def __init__(self, name: str):
        self.name = name
        self.results: List[TestResult] = []

    def add_result(self, result: TestResult):
        self.results.append(result)

    def get_success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    def get_success_rate(self) -> float:
        if not self.results:
            return 0.0
        return (self.get_success_count() / len(self.results)) * 100

    def get_avg_duration(self) -> float:
        if not self.results:
            return 0.0
        successful = [r.duration_ms for r in self.results if r.success]
        return sum(successful) / len(successful) if successful else 0.0

    def get_min_duration(self) -> float:
        if not self.results:
            return 0.0
        successful = [r.duration_ms for r in self.results if r.success]
        return min(successful) if successful else 0.0

    def get_max_duration(self) -> float:
        if not self.results:
            return 0.0
        successful = [r.duration_ms for r in self.results if r.success]
        return max(successful) if successful else 0.0


class HeadsetAPITester:
    """头显Server API测试器"""

    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = True):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()

        # 测试数据
        self.operator_token: Optional[str] = None
        self.headset_token: Optional[str] = None
        self.site_id: Optional[str] = None
        self.app_code: Optional[str] = None
        self.operator_id: Optional[str] = None

        # 测试统计
        self.stats: Dict[str, APITestStats] = {
            'pre_authorize': APITestStats('预授权查询'),
            'authorize': APITestStats('游戏授权'),
            'upload_session': APITestStats('上传会话数据')
        }

    def print_header(self, text: str):
        """打印标题"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

    def print_success(self, text: str):
        """打印成功信息"""
        print(f"{Colors.GREEN}✓ {text}{Colors.END}")

    def print_error(self, text: str):
        """打印错误信息"""
        print(f"{Colors.RED}✗ {text}{Colors.END}")

    def print_info(self, text: str):
        """打印信息"""
        print(f"{Colors.CYAN}ℹ {text}{Colors.END}")

    def setup(self) -> bool:
        """准备测试：登录并获取Headset Token"""
        self.print_header("准备测试环境")

        # 1. 运营商登录
        if not self._operator_login():
            self.print_error("运营商登录失败，无法继续测试")
            return False

        # 2. 获取运营商信息
        if not self._get_operator_info():
            self.print_error("获取运营商信息失败，无法继续测试")
            return False

        # 3. 生成Headset Token
        if not self._create_headset_token():
            self.print_error("生成Headset Token失败，无法继续测试")
            return False

        self.print_success("测试环境准备完成！\n")
        return True

    def _operator_login(self) -> bool:
        """运营商登录"""
        print("1. 运营商登录...")
        url = f"{self.base_url}/auth/operators/login"
        payload = {
            "username": self.username,
            "password": self.password,
            "captcha_key": "test-bypass",  # 测试环境绕过key
            "captcha_code": "0000"          # 测试环境绕过码
        }

        try:
            response = self.session.post(url, json=payload, verify=self.verify_ssl)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.operator_token = data["data"]["access_token"]
                    self.print_success(f"运营商登录成功: {self.username}")
                    return True

            self.print_error(f"登录失败: {response.status_code} - {response.text[:100]}")
            return False
        except Exception as e:
            self.print_error(f"登录异常: {str(e)}")
            return False

    def _get_operator_info(self) -> bool:
        """获取运营商信息"""
        print("2. 获取运营商信息...")
        headers = {"Authorization": f"Bearer {self.operator_token}"}

        try:
            # 获取运营商基本信息
            response = self.session.get(f"{self.base_url}/operators/me", headers=headers, verify=self.verify_ssl)
            if response.status_code == 200:
                data = response.json()
                self.operator_id = data.get("operator_id")

            # 获取运营点列表
            sites_response = self.session.get(f"{self.base_url}/operators/me/sites", headers=headers, verify=self.verify_ssl)
            if sites_response.status_code == 200:
                sites_data = sites_response.json()
                sites = sites_data.get("data", {}).get("sites", [])
                if sites:
                    full_site_id = sites[0]["site_id"]
                    self.site_id = full_site_id.replace("site_", "") if full_site_id.startswith("site_") else full_site_id

                    # 获取已授权应用
                    apps_response = self.session.get(f"{self.base_url}/operators/me/applications", headers=headers, verify=self.verify_ssl)
                    if apps_response.status_code == 200:
                        apps_data = apps_response.json()
                        apps = apps_data.get("data", {}).get("applications", [])
                        if apps:
                            self.app_code = apps[0]["app_code"]
                            self.print_success(f"运营点: {self.site_id}, 应用: {self.app_code}")
                            return True
                        else:
                            self.print_error("没有已授权的应用")
                            return False
                else:
                    self.print_error("没有运营点")
                    return False

            self.print_error("获取运营信息失败")
            return False
        except Exception as e:
            self.print_error(f"获取信息异常: {str(e)}")
            return False

    def _create_headset_token(self) -> bool:
        """创建Headset Token"""
        print("3. 生成Headset Token...")
        url = f"{self.base_url}/operators/generate-headset-token"
        headers = {"Authorization": f"Bearer {self.operator_token}"}

        try:
            response = self.session.post(url, headers=headers, verify=self.verify_ssl)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.headset_token = data["data"]["token"]
                    self.print_success(f"Headset Token生成成功 (长度: {len(self.headset_token)})")
                    return True

            self.print_error(f"Token生成失败: {response.status_code}")
            return False
        except Exception as e:
            self.print_error(f"Token生成异常: {str(e)}")
            return False

    def test_pre_authorize(self) -> TestResult:
        """测试预授权接口"""
        url = f"{self.base_url}/auth/game/pre-authorize"
        headers = {"Authorization": f"Bearer {self.headset_token}"}
        payload = {
            "app_code": self.app_code,
            "site_id": self.site_id,
            "player_count": 2
        }

        try:
            start_time = time.time()
            response = self.session.post(url, headers=headers, json=payload, verify=self.verify_ssl)
            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return TestResult(True, duration_ms)

            return TestResult(False, duration_ms, f"HTTP {response.status_code}")
        except Exception as e:
            return TestResult(False, 0, str(e))

    def test_authorize(self) -> tuple[TestResult, Optional[str]]:
        """测试游戏授权接口，返回(结果, session_id)"""
        url = f"{self.base_url}/auth/game/authorize"
        headers = {"Authorization": f"Bearer {self.headset_token}"}
        payload = {
            "app_code": self.app_code,
            "site_id": self.site_id,
            "player_count": 2,
            "headset_ids": ["test_headset_001", "test_headset_002"]
        }

        try:
            start_time = time.time()
            response = self.session.post(url, headers=headers, json=payload, verify=self.verify_ssl)
            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    session_id = data["data"].get("session_id")
                    return TestResult(True, duration_ms), session_id

            # 打印错误详情用于调试
            error_msg = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                if error_data.get("error"):
                    error_msg += f" - {error_data['error'].get('message', '')}"
            except:
                pass
            return TestResult(False, duration_ms, error_msg), None
        except Exception as e:
            return TestResult(False, 0, str(e)), None

    def test_upload_session(self, session_id: str) -> TestResult:
        """测试上传会话数据接口"""
        url = f"{self.base_url}/auth/game/session/upload"
        headers = {"Authorization": f"Bearer {self.headset_token}"}
        payload = {
            "session_id": session_id,
            "start_time": datetime.utcnow().isoformat() + "Z",
            "end_time": datetime.utcnow().isoformat() + "Z",
            "process_info": "test_data: true\nscore: 1500",
            "headset_devices": [
                {
                    "device_id": "test_headset_001",
                    "device_name": "测试设备1",
                    "start_time": datetime.utcnow().isoformat() + "Z",
                    "end_time": datetime.utcnow().isoformat() + "Z",
                    "process_info": "score: 800"
                },
                {
                    "device_id": "test_headset_002",
                    "device_name": "测试设备2",
                    "start_time": datetime.utcnow().isoformat() + "Z",
                    "end_time": datetime.utcnow().isoformat() + "Z",
                    "process_info": "score: 700"
                }
            ]
        }

        try:
            start_time = time.time()
            response = self.session.post(url, headers=headers, json=payload, verify=self.verify_ssl)
            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return TestResult(True, duration_ms)

            return TestResult(False, duration_ms, f"HTTP {response.status_code}")
        except Exception as e:
            return TestResult(False, 0, str(e))

    def run_tests(self, count: int, delay: float):
        """运行测试"""
        self.print_header(f"开始执行 {count} 次测试 (间隔 {delay} 秒)")

        for i in range(count):
            print(f"\n{Colors.BOLD}--- 第 {i+1}/{count} 次测试 ---{Colors.END}")

            # 1. 预授权测试
            print("  [1/3] 测试预授权接口...", end=" ")
            result = self.test_pre_authorize()
            self.stats['pre_authorize'].add_result(result)
            if result.success:
                print(f"{Colors.GREEN}✓ {result.duration_ms:.0f}ms{Colors.END}")
            else:
                print(f"{Colors.RED}✗ {result.error_msg}{Colors.END}")

            # 2. 游戏授权测试
            print("  [2/3] 测试游戏授权接口...", end=" ")
            result, session_id = self.test_authorize()
            self.stats['authorize'].add_result(result)
            if result.success:
                print(f"{Colors.GREEN}✓ {result.duration_ms:.0f}ms{Colors.END}")

                # 3. 上传会话数据测试 (仅当授权成功时)
                print("  [3/3] 测试上传会话接口...", end=" ")
                upload_result = self.test_upload_session(session_id)
                self.stats['upload_session'].add_result(upload_result)
                if upload_result.success:
                    print(f"{Colors.GREEN}✓ {upload_result.duration_ms:.0f}ms{Colors.END}")
                else:
                    print(f"{Colors.RED}✗ {upload_result.error_msg}{Colors.END}")
            else:
                print(f"{Colors.RED}✗ {result.error_msg}{Colors.END}")
                # 授权失败，跳过上传测试
                self.stats['upload_session'].add_result(TestResult(False, 0, "授权失败，跳过"))

            # 延迟
            if i < count - 1:
                time.sleep(delay)

    def print_statistics(self):
        """打印统计结果"""
        self.print_header("测试统计报告")

        print(f"{'接口名称':<20} {'成功率':<12} {'平均延迟':<12} {'最小延迟':<12} {'最大延迟':<12}")
        print("-" * 70)

        for key, stats in self.stats.items():
            success_rate = stats.get_success_rate()
            avg_duration = stats.get_avg_duration()
            min_duration = stats.get_min_duration()
            max_duration = stats.get_max_duration()

            # 根据成功率着色
            if success_rate >= 95:
                color = Colors.GREEN
            elif success_rate >= 80:
                color = Colors.YELLOW
            else:
                color = Colors.RED

            print(f"{stats.name:<20} {color}{success_rate:>6.1f}%{Colors.END}     "
                  f"{avg_duration:>8.0f}ms    {min_duration:>8.0f}ms    {max_duration:>8.0f}ms")

        print("\n" + "="*70)
        total_tests = sum(len(s.results) for s in self.stats.values())
        total_success = sum(s.get_success_count() for s in self.stats.values())
        overall_success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0

        print(f"总体成功率: {Colors.BOLD}{overall_success_rate:.1f}%{Colors.END} ({total_success}/{total_tests})")
        print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description='头显Server API性能测试工具')
    parser.add_argument('--base-url', required=True, help='API基础URL')
    parser.add_argument('--username', required=True, help='运营商用户名')
    parser.add_argument('--password', required=True, help='运营商密码')
    parser.add_argument('--count', type=int, default=10, help='测试次数 (默认10)')
    parser.add_argument('--delay', type=float, default=1.0, help='测试间隔秒数 (默认1.0)')

    args = parser.parse_args()

    # 判断是否需要禁用SSL验证 (开发服务器和localhost)
    verify_ssl = not (args.base_url.startswith('https://10.') or
                      'localhost' in args.base_url or
                      '127.0.0.1' in args.base_url)

    # 创建测试器
    tester = HeadsetAPITester(args.base_url, args.username, args.password, verify_ssl)

    # 准备测试环境
    if not tester.setup():
        print("\n测试准备失败，退出。")
        sys.exit(1)

    # 运行测试
    tester.run_tests(args.count, args.delay)

    # 打印统计
    tester.print_statistics()


if __name__ == "__main__":
    main()
