"""运营商充值功能测试

测试流程：
1. 运营商登录
2. 查询当前余额
3. 创建充值订单
4. 模拟支付回调
5. 验证余额更新
"""
import requests
from decimal import Decimal

BASE_URL = "http://localhost:8000/api/v1"

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


class RechargeTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.operator_id = None
        self.order_id = None
        self.initial_balance = None
        self.recharge_amount = "100.00"  # 充值100元

    def login(self, username="test_operator_110834", password="Test123456"):
        """运营商登录"""
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
        operator_data = result["data"]["operator"]
        self.operator_id = operator_data.get("id") or operator_data.get("operator_id")

        print_success("登录成功")
        print(f"  运营商ID: {self.operator_id}")
        print(f"  Token: {self.token[:30]}...")
        return True

    def get_headers(self):
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_balance(self):
        """查询当前余额"""
        print_section("2. 查询当前余额")

        response = requests.get(
            f"{self.base_url}/operators/me/balance",
            headers=self.get_headers()
        )

        if response.status_code != 200:
            print_error(f"查询失败: {response.text}")
            return False

        result = response.json()
        data = result.get("data", result)
        self.initial_balance = Decimal(str(data.get("balance", "0.00")))

        print_success(f"当前余额: {self.initial_balance}元")
        return True

    def create_recharge_order(self):
        """创建充值订单"""
        print_section("3. 创建充值订单")

        data = {
            "amount": self.recharge_amount,
            "payment_method": "wechat"
        }

        print_info(f"充值金额: {self.recharge_amount}元")
        print_info("支付方式: 微信支付")

        response = requests.post(
            f"{self.base_url}/operators/me/recharge",
            json=data,
            headers=self.get_headers()
        )

        if response.status_code != 201:
            print_error(f"创建订单失败: {response.text}")
            return False

        result = response.json()
        order_data = result.get("data", result)
        self.order_id = order_data.get("order_id")

        print_success("充值订单创建成功")
        print(f"  订单ID: {self.order_id}")
        print(f"  充值金额: {order_data.get('amount')}元")
        print(f"  支付方式: {order_data.get('payment_method')}")
        print(f"  过期时间: {order_data.get('expires_at')}")

        return True

    def simulate_payment_callback(self):
        """模拟支付回调"""
        print_section("4. 模拟支付回调")

        if not self.order_id:
            print_error("订单ID为空，无法模拟回调")
            return False

        # 构造支付回调数据
        callback_data = {
            "order_id": self.order_id,
            "transaction_id": f"wx_test_{self.order_id[-12:]}",
            "paid_amount": self.recharge_amount,
            "status": "success",
            "paid_at": "2025-10-16T11:30:00"
        }

        print_info(f"模拟支付成功回调...")
        print(f"  第三方交易ID: {callback_data['transaction_id']}")

        # 注意：支付回调不需要认证
        response = requests.post(
            f"{self.base_url}/webhooks/payment/wechat",
            json=callback_data
        )

        if response.status_code != 200:
            print_error(f"支付回调失败: {response.text}")
            return False

        result = response.json()
        print_success("支付回调处理成功")
        print(f"  处理结果: {result.get('message')}")

        return True

    def verify_balance_updated(self):
        """验证余额已更新"""
        print_section("5. 验证余额更新")

        response = requests.get(
            f"{self.base_url}/operators/me/balance",
            headers=self.get_headers()
        )

        if response.status_code != 200:
            print_error(f"查询失败: {response.text}")
            return False

        result = response.json()
        data = result.get("data", result)
        new_balance = Decimal(str(data.get("balance", "0.00")))

        expected_balance = self.initial_balance + Decimal(self.recharge_amount)

        print_info(f"初始余额: {self.initial_balance}元")
        print_info(f"充值金额: {self.recharge_amount}元")
        print_info(f"预期余额: {expected_balance}元")
        print_info(f"实际余额: {new_balance}元")

        if new_balance == expected_balance:
            print_success("余额更新正确！")
            return True
        else:
            print_error(f"余额不匹配！预期{expected_balance}元，实际{new_balance}元")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print_section("运营商充值功能测试")
        print_info("开始测试...")

        # 1. 登录
        if not self.login():
            return False

        # 2. 查询初始余额
        if not self.get_balance():
            return False

        # 3. 创建充值订单
        if not self.create_recharge_order():
            return False

        # 4. 模拟支付回调
        if not self.simulate_payment_callback():
            return False

        # 5. 验证余额更新
        if not self.verify_balance_updated():
            return False

        print_section("测试完成")
        print_success("充值功能测试全部通过！")
        print("\n下一步:")
        print("  1. 测试游戏会话授权")
        print("  2. 测试实时计费扣费")

        return True


if __name__ == "__main__":
    try:
        tester = RechargeTester()
        success = tester.run_all_tests()
        exit(0 if success else 1)
    except Exception as e:
        print_error(f"测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
