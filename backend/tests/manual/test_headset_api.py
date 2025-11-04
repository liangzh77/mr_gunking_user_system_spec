#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
头显Server API 完整测试脚本

测试所有头显Server相关的接口：
1. 创建Headset Token (POST /api/v1/operators/sites/{site_id}/create-headset-token)
2. 预授权查询 (POST /api/v1/auth/game/pre-authorize)
3. 游戏授权 (POST /api/v1/auth/game/authorize)
4. 上传游戏Session (POST /api/v1/auth/game/session/upload)
"""

import sys
import io
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000/api/v1"

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    """打印信息"""
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")


def print_response(response: requests.Response):
    """打印响应详情"""
    print(f"  状态码: {response.status_code}")
    try:
        data = response.json()
        print(f"  响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"  响应: {response.text[:200]}")


class HeadsetAPITester:
    """头显Server API测试器"""

    def __init__(self):
        self.session = requests.Session()
        self.operator_token = None
        self.operator_id = None  # 存储operator_id
        self.headset_token = None
        self.site_id = None
        self.app_code = None
        self.session_id = None
        self.authorization_token = None

    def run_all_tests(self):
        """运行所有测试"""
        print_header("头显Server API 完整测试")

        # 测试计数
        total = 0
        passed = 0

        # 1. 准备工作：运营商登录
        total += 1
        if self.test_operator_login():
            passed += 1

        # 2. 准备工作：获取运营商信息
        total += 1
        if self.test_get_operator_info():
            passed += 1

        # 3. 创建Headset Token
        total += 1
        if self.test_create_headset_token():
            passed += 1
        else:
            print_error("无法继续测试，Headset Token创建失败")
            return

        # 4. 预授权查询
        total += 1
        if self.test_pre_authorize():
            passed += 1

        # 5. 游戏授权
        total += 1
        if self.test_game_authorize():
            passed += 1
        else:
            print_error("无法继续测试，游戏授权失败")
            return

        # 6. 上传游戏Session
        total += 1
        if self.test_upload_session():
            passed += 1

        # 总结
        print_header(f"测试完成: {passed}/{total} 通过")
        if passed == total:
            print_success(f"所有测试通过！🎉")
        else:
            print_error(f"{total - passed} 个测试失败")

    def test_operator_login(self) -> bool:
        """测试运营商登录"""
        print_header("1. 运营商登录 (准备工作)")

        url = f"{BASE_URL}/auth/operators/login"
        payload = {
            "username": "headset_test_op",
            "password": "Test123456"
        }

        try:
            response = self.session.post(url, json=payload)
            print_response(response)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.operator_token = data["data"]["access_token"]
                    print_success("运营商登录成功")
                    return True

            print_error("运营商登录失败")
            return False

        except Exception as e:
            print_error(f"请求失败: {str(e)}")
            return False

    def test_get_operator_info(self) -> bool:
        """获取运营商信息（获取site_id）"""
        print_header("2. 获取运营商信息 (准备工作)")

        url = f"{BASE_URL}/operators/me"
        headers = {"Authorization": f"Bearer {self.operator_token}"}

        try:
            response = self.session.get(url, headers=headers)
            print_response(response)

            if response.status_code == 200:
                data = response.json()
                # API直接返回运营商信息对象，无success字段
                # 需要调用sites API获取运营点列表
                self.operator_id = data.get("operator_id")  # 保存operator_id用于session_id生成

                # 获取运营点列表
                sites_response = self.session.get(
                    f"{BASE_URL}/operators/me/sites",
                    headers=headers
                )
                print_info(f"Sites API Status: {sites_response.status_code}")
                if sites_response.status_code == 200:
                    sites_data = sites_response.json()
                    print_info(f"Sites Response: {json.dumps(sites_data, ensure_ascii=False)[:200]}")
                    sites = sites_data.get("data", {}).get("sites", [])
                    if sites:
                        # site_id格式是"site_uuid"，需要去掉site_前缀
                        full_site_id = sites[0]["site_id"]
                        self.site_id = full_site_id.replace("site_", "") if full_site_id.startswith("site_") else full_site_id

                        # 获取已授权应用列表
                        apps_response = self.session.get(
                            f"{BASE_URL}/operators/me/applications",  # 路径是/me/applications
                            headers=headers
                        )
                        if apps_response.status_code == 200:
                            apps_data = apps_response.json()
                            apps = apps_data.get("data", {}).get("applications", [])
                            if apps:
                                self.app_code = apps[0]["app_code"]
                                print_success(f"获取运营信息成功 - Site ID: {self.site_id}, App Code: {self.app_code}")
                                return True
                            else:
                                print_error("没有已授权的应用")
                                return False
                    else:
                        print_error("没有运营点")
                        return False

            print_error("获取运营商信息失败")
            return False

        except Exception as e:
            print_error(f"请求失败: {str(e)}")
            return False

    def test_create_headset_token(self) -> bool:
        """测试创建Headset Token"""
        print_header("3. 创建Headset Token")

        url = f"{BASE_URL}/operators/generate-token"  # 正确的路径
        headers = {"Authorization": f"Bearer {self.operator_token}"}
        # 不需要payload，直接POST即可

        try:
            response = self.session.post(url, headers=headers)  # 不需要json=payload
            print_response(response)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.headset_token = data["data"]["token"]  # 字段是token不是headset_token
                    print_success(f"Headset Token创建成功")
                    print_info(f"Token: {self.headset_token[:50]}...")
                    return True

            print_error("Headset Token创建失败")
            return False

        except Exception as e:
            print_error(f"请求失败: {str(e)}")
            return False

    def test_pre_authorize(self) -> bool:
        """测试预授权查询"""
        print_header("4. 预授权查询 (可选)")

        url = f"{BASE_URL}/auth/game/pre-authorize"
        headers = {
            "Authorization": f"Bearer {self.headset_token}",
            "X-Session-ID": self._generate_session_id()
        }
        payload = {
            "app_code": self.app_code,
            "site_id": self.site_id,
            "player_count": 2  # 字段名是player_count而不是estimated_player_count
        }

        try:
            response = self.session.post(url, headers=headers, json=payload)
            print_response(response)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print_success("预授权查询成功")
                    can_auth = data["data"]["can_authorize"]
                    if can_auth:
                        print_success(f"✓ 可以授权")
                    else:
                        print_error(f"✗ 无法授权: {data['data'].get('reason', 'Unknown')}")
                    return True

            print_error("预授权查询失败")
            return False

        except Exception as e:
            print_error(f"请求失败: {str(e)}")
            return False

    def test_game_authorize(self) -> bool:
        """测试游戏授权"""
        print_header("5. 游戏授权 (核心接口)")

        self.session_id = self._generate_session_id()
        url = f"{BASE_URL}/auth/game/authorize"
        headers = {
            "Authorization": f"Bearer {self.headset_token}",
            "X-Session-ID": self.session_id
        }
        payload = {
            "app_code": self.app_code,
            "site_id": self.site_id,
            "player_count": 2
        }

        try:
            response = self.session.post(url, headers=headers, json=payload)
            print_response(response)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.authorization_token = data["data"]["authorization_token"]
                    print_success("游戏授权成功")
                    print_info(f"Session ID: {self.session_id}")
                    print_info(f"扣费金额: {data['data']['total_cost']}")  # 字段名是total_cost
                    print_info(f"授权后余额: {data['data']['balance_after']}")  # 只有授权后余额
                    return True

            print_error("游戏授权失败")
            return False

        except Exception as e:
            print_error(f"请求失败: {str(e)}")
            return False

    def test_upload_session(self) -> bool:
        """测试上传游戏Session"""
        print_header("6. 上传游戏Session (可选)")

        url = f"{BASE_URL}/auth/game/session/upload"
        headers = {
            "Authorization": f"Bearer {self.headset_token}",
            "X-Session-ID": self.session_id
        }
        payload = {
            "session_id": self.session_id,  # 需要提供session_id
            "session_records": [
                {
                    "headset_id": "headset_001",
                    "play_time_seconds": 1800
                },
                {
                    "headset_id": "headset_002",
                    "play_time_seconds": 1750
                }
            ]
        }

        try:
            response = self.session.post(url, headers=headers, json=payload)
            print_response(response)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print_success("Session上传成功")
                    print_info(f"消息: {data.get('message', '游戏信息上传成功')}")
                    return True

            print_error("Session上传失败")
            return False

        except Exception as e:
            print_error(f"请求失败: {str(e)}")
            return False

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        import random
        import string

        # 格式: {operatorId}_{13位毫秒时间戳}_{16位随机字符}
        # 使用真实的operator_id
        timestamp_ms = int(time.time() * 1000)
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

        return f"{self.operator_id}_{timestamp_ms}_{random_str}"


if __name__ == "__main__":
    tester = HeadsetAPITester()
    tester.run_all_tests()
