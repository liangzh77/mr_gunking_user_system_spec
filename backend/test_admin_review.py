"""管理员审批授权申请功能测试

测试流程：
1. 管理员登录
2. 查询待审批的授权申请列表
3. 审批授权申请（通过）
4. 验证审批结果
5. 测试拒绝功能
"""
import requests

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


class AdminReviewTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.admin_token = None
        self.pending_requests = []

    def admin_login(self, username="admin", password="Admin123"):
        """管理员登录"""
        print_section("1. 管理员登录")

        response = requests.post(
            f"{self.base_url}/admin/login",
            json={"username": username, "password": password}
        )

        if response.status_code != 200:
            print_error(f"登录失败: {response.text}")
            return False

        result = response.json()
        self.admin_token = result["access_token"]

        print_success("管理员登录成功")
        print(f"  Token: {self.admin_token[:30]}...")
        return True

    def get_headers(self):
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }

    def get_application_requests(self, status=None):
        """查询授权申请列表"""
        print_section("2. 查询授权申请列表")

        params = {}
        if status:
            params["status"] = status

        response = requests.get(
            f"{self.base_url}/admins/applications/requests",
            params=params,
            headers=self.get_headers()
        )

        if response.status_code != 200:
            print_error(f"查询失败: {response.text}")
            return False

        result = response.json()
        self.pending_requests = [r for r in result.get("items", []) if r["status"] == "pending"]

        print_success(f"查询成功，共 {result.get('total', 0)} 条申请记录")
        print_info(f"待审批: {len(self.pending_requests)} 条")

        for req in result.get("items", [])[:5]:  # 显示前5条
            print(f"\n  申请ID: {req['request_id']}")
            print(f"  应用: {req['app_name']} ({req['app_code']})")
            print(f"  申请理由: {req['reason'][:50]}...")
            print(f"  状态: {req['status']}")

        return True

    def approve_request(self, request_id):
        """审批通过"""
        print_section(f"3. 审批通过申请 {request_id}")

        response = requests.post(
            f"{self.base_url}/admins/applications/requests/{request_id}/review",
            json={"action": "approve"},
            headers=self.get_headers()
        )

        if response.status_code != 200:
            print_error(f"审批失败: {response.text}")
            return False

        result = response.json()

        print_success("审批成功")
        print(f"  申请ID: {result['request_id']}")
        print(f"  应用: {result['app_name']}")
        print(f"  状态: {result['status']}")
        print(f"  审批人: {result.get('reviewed_by', 'N/A')}")
        print(f"  审批时间: {result.get('reviewed_at', 'N/A')}")

        return True

    def reject_request(self, request_id):
        """审批拒绝"""
        print_section(f"4. 审批拒绝申请 {request_id}")

        reject_reason = "该应用暂未对您的客户分类开放授权，请先升级客户等级"

        response = requests.post(
            f"{self.base_url}/admins/applications/requests/{request_id}/review",
            json={
                "action": "reject",
                "reject_reason": reject_reason
            },
            headers=self.get_headers()
        )

        if response.status_code != 200:
            print_error(f"审批失败: {response.text}")
            return False

        result = response.json()

        print_success("审批拒绝成功")
        print(f"  申请ID: {result['request_id']}")
        print(f"  应用: {result['app_name']}")
        print(f"  状态: {result['status']}")
        print(f"  拒绝原因: {result.get('reject_reason', 'N/A')}")
        print(f"  审批人: {result.get('reviewed_by', 'N/A')}")

        return True

    def verify_approval(self):
        """验证审批结果"""
        print_section("5. 验证审批结果")

        # 重新查询申请列表
        response = requests.get(
            f"{self.base_url}/admins/applications/requests",
            params={"status": "approved"},
            headers=self.get_headers()
        )

        if response.status_code != 200:
            print_error(f"查询失败: {response.text}")
            return False

        result = response.json()
        approved_count = result.get("total", 0)

        print_success(f"已通过的申请数量: {approved_count}")

        return True

    def run_all_tests(self):
        """运行所有测试"""
        print_section("管理员审批授权申请功能测试")
        print_info("开始测试...")

        # 1. 管理员登录
        if not self.admin_login():
            return False

        # 2. 查询申请列表
        if not self.get_application_requests():
            return False

        if len(self.pending_requests) == 0:
            print_info("\n没有待审批的申请，测试结束")
            print_info("\n提示：你可以通过运营商账号提交应用授权申请来测试")
            return True

        # 3. 审批通过第一个申请
        first_request = self.pending_requests[0]
        if not self.approve_request(first_request["request_id"]):
            return False

        # 4. 如果有第二个待审批申请，测试拒绝功能
        if len(self.pending_requests) > 1:
            second_request = self.pending_requests[1]
            if not self.reject_request(second_request["request_id"]):
                return False

        # 5. 验证审批结果
        if not self.verify_approval():
            return False

        print_section("测试完成")
        print_success("管理员审批功能测试全部通过！")
        print("\n测试总结:")
        print(f"  原始待审批数量: {len(self.pending_requests)}")
        print(f"  测试通过: 1 个申请")
        if len(self.pending_requests) > 1:
            print(f"  测试拒绝: 1 个申请")

        return True


if __name__ == "__main__":
    try:
        tester = AdminReviewTester()
        success = tester.run_all_tests()
        exit(0 if success else 1)
    except Exception as e:
        print_error(f"测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
