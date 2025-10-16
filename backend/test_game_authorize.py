"""游戏授权和扣费功能测试

测试流程：
1. 查询运营商当前余额
2. 发起游戏授权请求（模拟头显Server）
3. 验证授权成功并扣费
4. 验证余额减少
5. 测试幂等性（重复请求不重复扣费）
"""
import requests
import time
import hmac
import hashlib
import base64
import secrets
from decimal import Decimal

BASE_URL = "http://localhost:8000/api/v1"

# 测试数据（从数据库查询获得）
OPERATOR_ID = "4f75efbb-d69c-4211-b103-ccd3e789a222"
API_KEY = "ae4196ee20d37e6f286059273e3c538a4840c4b02da68444fcdabd8915fd4c50"
SITE_ID = "7322072f-badf-40e2-908f-2bdad1f9ad5f"
APP_ID = "439e1dd7-4f19-4ab2-9651-78142aec16ba"

class Colors:
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


class GameAuthorizeTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.operator_id = OPERATOR_ID
        self.api_key = API_KEY
        self.site_id = SITE_ID
        self.app_id = APP_ID
        self.token = None
        self.initial_balance = None
        self.player_count = 2  # 测试2个玩家
        self.unit_price = Decimal("10.00")  # MR枪王争霸：10元/人
        self.expected_cost = Decimal(str(self.player_count)) * self.unit_price
        self.session_id = None
        self.authorization_token = None

    def login(self, username="test_operator_110834", password="Test123456"):
        """运营商登录（用于查询余额）"""
        print_section("1. 运营商登录")

        response = requests.post(
            f"{self.base_url}/auth/operators/login",
            json={"username": username, "password": password}
        )

        if response.status_code != 200:
            print_error(f"登录失败: {response.text}")
            return False

        result = response.json()
        self.token = result["data"]["access_token"]

        print_success("登录成功")
        return True

    def get_balance(self):
        """查询当前余额"""
        print_section("2. 查询当前余额")

        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/operators/me/balance",
            headers=headers
        )

        if response.status_code != 200:
            print_error(f"查询失败: {response.text}")
            return False

        result = response.json()
        data = result.get("data", result)
        self.initial_balance = Decimal(str(data.get("balance", "0.00")))

        print_success(f"当前余额: {self.initial_balance}元")
        return True

    def generate_session_id(self):
        """生成会话ID

        格式: {operatorId}_{timestamp}_{random16}
        """
        timestamp = int(time.time())
        random_part = secrets.token_hex(8)  # 16个十六进制字符 = 8字节
        session_id = f"{self.operator_id}_{timestamp}_{random_part}"
        return session_id

    def generate_signature(self, session_id, timestamp, request_body):
        """生成HMAC-SHA256签名

        签名内容: {session_id}|{timestamp}|{request_body_json}
        使用API Key作为密钥
        """
        import json

        # 构造签名消息
        message = f"{session_id}|{timestamp}|{json.dumps(request_body, sort_keys=True)}"

        # 使用API Key生成HMAC-SHA256签名
        signature = hmac.new(
            self.api_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()

        # Base64编码
        return base64.b64encode(signature).decode('utf-8')

    def authorize_game(self):
        """发起游戏授权请求"""
        print_section("3. 发起游戏授权请求")

        # 生成会话ID和时间戳
        self.session_id = self.generate_session_id()
        timestamp = int(time.time())

        # 请求体
        request_body = {
            "app_id": self.app_id,
            "site_id": self.site_id,
            "player_count": self.player_count
        }

        # 生成签名
        signature = self.generate_signature(self.session_id, timestamp, request_body)

        # 构造headers
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Session-ID": self.session_id,
            "X-Timestamp": str(timestamp),
            "X-Signature": signature
        }

        print_info(f"会话ID: {self.session_id}")
        print_info(f"玩家数量: {self.player_count}人")
        print_info(f"单人价格: {self.unit_price}元")
        print_info(f"预期费用: {self.expected_cost}元")

        response = requests.post(
            f"{self.base_url}/auth/game/authorize",
            json=request_body,
            headers=headers
        )

        if response.status_code != 200:
            print_error(f"授权失败: {response.text}")
            return False

        result = response.json()
        data = result.get("data", result)

        self.authorization_token = data.get("authorization_token")
        actual_cost = Decimal(str(data.get("total_cost", "0")))
        balance_after = Decimal(str(data.get("balance_after", "0")))

        print_success("游戏授权成功")
        print(f"  授权Token: {self.authorization_token[:30]}...")
        print(f"  实际扣费: {actual_cost}元")
        print(f"  剩余余额: {balance_after}元")

        # 验证扣费金额
        if actual_cost == self.expected_cost:
            print_success("扣费金额正确")
        else:
            print_error(f"扣费金额不符！预期{self.expected_cost}元，实际{actual_cost}元")
            return False

        return True

    def verify_balance_deducted(self):
        """验证余额已扣减"""
        print_section("4. 验证余额扣减")

        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/operators/me/balance",
            headers=headers
        )

        if response.status_code != 200:
            print_error(f"查询失败: {response.text}")
            return False

        result = response.json()
        data = result.get("data", result)
        new_balance = Decimal(str(data.get("balance", "0.00")))

        expected_balance = self.initial_balance - self.expected_cost

        print_info(f"初始余额: {self.initial_balance}元")
        print_info(f"扣除费用: {self.expected_cost}元")
        print_info(f"预期余额: {expected_balance}元")
        print_info(f"实际余额: {new_balance}元")

        if new_balance == expected_balance:
            print_success("余额扣减正确！")
            return True
        else:
            print_error(f"余额不匹配！预期{expected_balance}元，实际{new_balance}元")
            return False

    def test_idempotency(self):
        """测试幂等性（重复请求不重复扣费）"""
        print_section("5. 测试幂等性")

        timestamp = int(time.time())

        request_body = {
            "app_id": self.app_id,
            "site_id": self.site_id,
            "player_count": self.player_count
        }

        signature = self.generate_signature(self.session_id, timestamp, request_body)

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Session-ID": self.session_id,  # 使用相同的session_id
            "X-Timestamp": str(timestamp),
            "X-Signature": signature
        }

        print_info(f"使用相同的会话ID发起第二次请求...")
        print_info(f"会话ID: {self.session_id}")

        response = requests.post(
            f"{self.base_url}/auth/game/authorize",
            json=request_body,
            headers=headers
        )

        if response.status_code not in [200, 409]:  # 200或409都是正常的
            print_error(f"请求失败: {response.text}")
            return False

        result = response.json()
        data = result.get("data", result)

        # 查询余额，验证没有重复扣费
        headers_balance = {"Authorization": f"Bearer {self.token}"}
        balance_response = requests.get(
            f"{self.base_url}/operators/me/balance",
            headers=headers_balance
        )

        balance_result = balance_response.json()
        balance_data = balance_result.get("data", balance_result)
        final_balance = Decimal(str(balance_data.get("balance", "0.00")))

        expected_balance = self.initial_balance - self.expected_cost

        if final_balance == expected_balance:
            print_success("幂等性测试通过！重复请求未重复扣费")
            print(f"  余额保持不变: {final_balance}元")
            return True
        else:
            print_error(f"幂等性失败！余额发生变化：{final_balance}元")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print_section("游戏授权和扣费功能测试")
        print_info("开始测试...")

        # 1. 登录
        if not self.login():
            return False

        # 2. 查询初始余额
        if not self.get_balance():
            return False

        # 3. 发起游戏授权
        if not self.authorize_game():
            return False

        # 4. 验证余额扣减
        if not self.verify_balance_deducted():
            return False

        # 5. 测试幂等性
        if not self.test_idempotency():
            return False

        print_section("测试完成")
        print_success("游戏授权和扣费功能测试全部通过！")
        print("\n测试总结:")
        print(f"  初始余额: {self.initial_balance}元")
        print(f"  扣费金额: {self.expected_cost}元 ({self.player_count}人 × {self.unit_price}元/人)")
        print(f"  最终余额: {self.initial_balance - self.expected_cost}元")
        print(f"  授权Token: {self.authorization_token[:40] if self.authorization_token else 'N/A'}...")
        print(f"  幂等性: 通过")

        return True


if __name__ == "__main__":
    try:
        tester = GameAuthorizeTester()
        success = tester.run_all_tests()
        exit(0 if success else 1)
    except Exception as e:
        print_error(f"测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
