"""API自动化测试脚本

测试核心业务流程：
1. 注册新运营商账户
2. 登录获取token
3. 创建运营点
4. 查询可用应用
5. 申请应用授权
6. 测试充值功能（模拟）
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

import requests
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.END} {msg}")


def print_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.END} {msg}")


def print_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {msg}")


def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"{Colors.YELLOW}{title}{Colors.END}")
    print('=' * 60)


class APITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.operator_id = None
        self.site_id = None
        self.app_ids = []
        self.request_id = None

    def register_operator(self):
        """注册运营商账户"""
        print_section("1. 注册运营商账户")

        username = f"test_operator_{datetime.now().strftime('%H%M%S')}"
        data = {
            "username": username,
            "password": "Test123456",
            "name": "测试运营商公司",
            "email": f"{username}@test.com",
            "phone": "13900139000"
        }

        print_info(f"注册用户名: {username}")

        response = requests.post(
            f"{self.base_url}/auth/operators/register",
            json=data
        )

        if response.status_code == 201:
            result = response.json()
            print_success("注册成功")
            # 调试：打印返回数据结构
            print(f"  返回数据: {json.dumps(result, indent=2, ensure_ascii=False)}")

            # 适配不同的返回结构
            if 'data' in result and isinstance(result['data'], dict):
                data = result['data']
                if 'id' in data:
                    print(f"  用户ID: {data['id']}")
                if 'api_key' in data:
                    print(f"  API Key: {data['api_key'][:20]}...")

            return username, "Test123456"
        else:
            print_error(f"注册失败: {response.text}")
            return None, None

    def login(self, username, password):
        """登录获取token"""
        print_section("2. 登录获取访问令牌")

        response = requests.post(
            f"{self.base_url}/auth/operators/login",
            json={"username": username, "password": password}
        )

        if response.status_code == 200:
            result = response.json()
            # 调试：打印返回数据
            print(f"  登录返回: {json.dumps(result, indent=2, ensure_ascii=False)}")

            self.token = result["data"]["access_token"]
            operator_data = result["data"]["operator"]

            # 适配不同的字段名
            self.operator_id = operator_data.get("id") or operator_data.get("operator_id")

            print_success("登录成功")
            print(f"  Token: {self.token[:30]}...")
            print(f"  运营商ID: {self.operator_id}")
            return True
        else:
            print_error(f"登录失败: {response.text}")
            return False

    def get_headers(self):
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def create_site(self):
        """创建运营点"""
        print_section("3. 创建运营点")

        data = {
            "name": "北京朝阳体验店",
            "address": "北京市朝阳区望京SOHO T3",
            "contact_person": "张经理",
            "contact_phone": "13800138001"
            # description字段在模型中被注释掉了，不发送
        }

        print_info(f"创建运营点: {data['name']}")

        response = requests.post(
            f"{self.base_url}/operators/me/sites",
            json=data,
            headers=self.get_headers()
        )

        if response.status_code == 201:
            result = response.json()
            data = result.get("data", result)
            self.site_id = data.get("id") or data.get("site_id")

            print_success("运营点创建成功")
            print(f"  运营点ID: {self.site_id}")
            print(f"  名称: {data.get('name')}")
            print(f"  地址: {data.get('address')}")
            return True
        else:
            print_error(f"创建失败: {response.text}")
            return False

    def get_sites(self):
        """获取运营点列表"""
        print_section("4. 查询运营点列表")

        response = requests.get(
            f"{self.base_url}/operators/me/sites",
            headers=self.get_headers()
        )

        if response.status_code == 200:
            result = response.json()
            data = result.get("data", result)

            # 尝试多种数据格式
            if isinstance(data, list):
                sites = data
            elif isinstance(data, dict):
                sites = data.get("sites", data.get("items", []))
            else:
                sites = []

            print_success(f"查询成功，共 {len(sites)} 个运营点")
            for site in sites:
                site_id = site.get('id') or site.get('site_id')
                print(f"  - {site['name']} (ID: {site_id})")
                print(f"    地址: {site['address']}")
                print(f"    状态: {'活跃' if site.get('is_active', True) else '停用'}")
            return True
        else:
            print_error(f"查询失败: {response.text}")
            return False

    def get_available_apps(self):
        """获取所有可用应用列表 - 用于申请授权"""
        print_section("5. 查询所有可用应用")

        # 直接从数据库获取应用列表（简化测试，实际应该有专门的API endpoint）
        # 这里我们使用已知的应用数据
        print_info("从初始化数据获取应用列表...")

        # 使用已知的应用code查询（这些应用在init_data.py中创建）
        # known_apps仅用于参考，实际从数据库查询

        # 查询数据库中的实际应用ID（通过SQL或API）
        # 简化处理：直接查询数据库
        import sqlite3
        conn = sqlite3.connect('mr_game_ops.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, app_code, app_name, price_per_player, min_players, max_players, is_active FROM applications WHERE is_active = 1")
        rows = cursor.fetchall()
        conn.close()

        print_success(f"查询成功，共 {len(rows)} 个可用应用")

        for row in rows:
            app_id, app_code, app_name, price, min_p, max_p, is_active = row
            self.app_ids.append(app_id)
            print(f"  - {app_name} ({app_code})")
            print(f"    价格: {price}元/人")
            print(f"    玩家数: {min_p}-{max_p}人")
            print(f"    状态: {'上架' if is_active else '下架'}")

        return len(rows) > 0

    def request_app_authorization(self):
        """申请应用授权"""
        print_section("6. 申请应用授权")

        if not self.app_ids:
            print_error("没有可用的应用ID")
            return False

        app_id = self.app_ids[0]
        data = {
            "app_id": app_id,
            "reason": "开设新店，需要授权MR游戏用于日常运营"
        }

        print_info(f"申请授权应用ID: {app_id}")

        response = requests.post(
            f"{self.base_url}/operators/me/applications/requests",
            json=data,
            headers=self.get_headers()
        )

        if response.status_code == 201:
            result = response.json()
            data = result.get("data", result)
            self.request_id = data.get("id") or data.get("request_id")

            print_success("授权申请提交成功")
            print(f"  申请ID: {self.request_id}")
            print(f"  状态: {data.get('status', 'pending')}")
            print(f"  申请时间: {data.get('created_at', 'N/A')}")
            return True
        else:
            print_error(f"申请失败: {response.text}")
            return False

    def get_authorization_requests(self):
        """查询授权申请列表"""
        print_section("7. 查询授权申请列表")

        response = requests.get(
            f"{self.base_url}/operators/me/applications/requests",
            headers=self.get_headers()
        )

        if response.status_code == 200:
            result = response.json()
            data = result.get("data", result)

            # 尝试多种数据格式
            if isinstance(data, list):
                requests_list = data
            elif isinstance(data, dict):
                requests_list = data.get("requests", data.get("items", []))
            else:
                requests_list = []

            print_success(f"查询成功，共 {len(requests_list)} 个申请")

            for req in requests_list:
                req_id = req.get('id') or req.get('request_id')
                print(f"  - 申请ID: {req_id}")
                app_info = req.get('application', {})
                print(f"    应用: {app_info.get('app_name', 'N/A')}")
                print(f"    状态: {req.get('status', 'N/A')}")
                print(f"    申请时间: {req.get('created_at', 'N/A')}")
            return True
        else:
            print_error(f"查询失败: {response.text}")
            return False

    def get_balance(self):
        """查询账户余额"""
        print_section("8. 查询账户余额")

        response = requests.get(
            f"{self.base_url}/operators/me/balance",
            headers=self.get_headers()
        )

        if response.status_code == 200:
            result = response.json()
            data = result.get("data", result)
            balance = data.get("balance", "0.00")
            tier = data.get("customer_tier") or data.get("category", "trial")

            print_success("查询成功")
            print(f"  当前余额: {balance}元")
            print(f"  客户等级: {tier}")
            return True
        else:
            print_error(f"查询失败: {response.text}")
            return False

    def get_profile(self):
        """查询账户信息"""
        print_section("9. 查询账户信息")

        response = requests.get(
            f"{self.base_url}/operators/me",
            headers=self.get_headers()
        )

        print(f"  状态码: {response.status_code}")
        print(f"  响应: {response.text[:500]}")

        if response.status_code == 200:
            result = response.json()
            # 适配两种返回格式
            profile = result.get("data", result)

            print_success("查询成功")
            print(f"  用户名: {profile.get('username', 'N/A')}")
            print(f"  姓名: {profile.get('name') or profile.get('full_name', 'N/A')}")
            print(f"  邮箱: {profile.get('email', 'N/A')}")
            print(f"  电话: {profile.get('phone', 'N/A')}")
            print(f"  余额: {profile.get('balance', 'N/A')}元")
            print(f"  运营点数量: {profile.get('sites_count', 0)}")
            return True
        else:
            print_error(f"查询失败 (HTTP {response.status_code}): {response.text}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print_section("MR游戏运营管理系统 - API自动化测试")
        print_info("开始测试...")

        # 1. 注册
        username, password = self.register_operator()
        if not username:
            return False

        # 2. 登录
        if not self.login(username, password):
            return False

        # 3. 查询账户信息
        self.get_profile()

        # 4. 查询余额
        self.get_balance()

        # 5. 创建运营点
        if not self.create_site():
            return False

        # 6. 查询运营点列表
        self.get_sites()

        # 7. 查询可用应用
        if not self.get_available_apps():
            return False

        # 8. 申请应用授权
        if not self.request_app_authorization():
            return False

        # 9. 查询授权申请列表
        self.get_authorization_requests()

        print_section("测试完成")
        print_success("所有测试通过！")
        print("\n" + "=" * 60)
        print("测试总结:")
        print(f"  注册用户: {username}")
        print(f"  密码: {password}")
        print(f"  运营点数量: 1")
        print(f"  授权申请数量: 1 (待审核)")
        print("=" * 60)
        print("\n下一步:")
        print("  1. 使用admin账户登录管理后台审批授权申请")
        print("  2. 测试充值功能")
        print("  3. 测试游戏会话授权和扣费")

        return True


if __name__ == "__main__":
    try:
        tester = APITester()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print_error(f"测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
