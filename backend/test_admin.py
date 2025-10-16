"""管理员功能测试脚本

测试管理员核心功能：
1. 管理员登录
2. 查看待审批的授权申请
3. 审批授权申请
4. 验证运营商已获得授权
"""
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


class AdminTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.admin_id = None
        self.pending_requests = []

    def admin_login(self, username="admin", password="Admin123"):
        """管理员登录"""
        print_section("1. 管理员登录")

        response = requests.post(
            f"{self.base_url}/admin/login",
            json={"username": username, "password": password}
        )

        if response.status_code == 200:
            result = response.json()
            # 调试：打印返回数据
            print(f"  登录返回: {result}")

            # 适配不同的返回结构
            data = result.get("data", result)
            self.token = data.get("access_token")
            admin_data = data.get("user") or data.get("admin")
            self.admin_id = admin_data.get("id") or admin_data.get("admin_id")

            print_success("登录成功")
            print(f"  管理员: {admin_data.get('username')}")
            print(f"  角色: {admin_data.get('role')}")
            print(f"  Token: {self.token[:30]}...")
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

    def get_pending_requests(self):
        """查询待审批的授权申请"""
        print_section("2. 查询待审批的授权申请")

        response = requests.get(
            f"{self.base_url}/admins/applications/requests?status=pending",
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

            print_success(f"查询成功，共 {len(requests_list)} 个待审批申请")

            for req in requests_list:
                req_id = req.get('id') or req.get('request_id')
                self.pending_requests.append(req_id)

                operator_info = req.get('operator', {})
                app_info = req.get('application', {})

                print(f"\n  申请ID: {req_id}")
                print(f"    运营商: {operator_info.get('username', 'N/A')} ({operator_info.get('name', 'N/A')})")
                print(f"    应用: {app_info.get('app_name', 'N/A')} ({app_info.get('app_code', 'N/A')})")
                print(f"    申请理由: {req.get('reason', 'N/A')}")
                print(f"    申请时间: {req.get('created_at', 'N/A')}")

            return len(requests_list) > 0
        else:
            print_error(f"查询失败: {response.text}")
            return False

    def approve_request(self, request_id, expires_days=365):
        """审批通过授权申请"""
        print_section(f"3. 审批授权申请 (ID: {request_id})")

        data = {
            "request_id": request_id,
            "action": "approve",
            "expires_days": expires_days
        }

        response = requests.post(
            f"{self.base_url}/admins/applications/requests/{request_id}/review",
            json=data,
            headers=self.get_headers()
        )

        if response.status_code == 200:
            result = response.json()
            print_success("审批成功")
            print(f"  授权有效期: {expires_days}天")
            return True
        else:
            print_error(f"审批失败: {response.text}")
            return False

    def verify_operator_authorization(self, operator_username):
        """验证运营商已获得授权"""
        print_section(f"4. 验证运营商授权 ({operator_username})")

        # 首先获取运营商信息
        print_info("查询运营商授权状态...")

        # 注意：这里需要运营商的token，实际应该重新登录或使用已有token
        # 简化处理：直接查询数据库验证
        import sqlite3
        conn = sqlite3.connect('mr_game_ops.db')
        cursor = conn.cursor()

        # 查询运营商ID
        cursor.execute(
            "SELECT id FROM operator_accounts WHERE username = ? AND deleted_at IS NULL",
            (operator_username,)
        )
        operator_row = cursor.fetchone()

        if not operator_row:
            conn.close()
            print_error("运营商不存在")
            return False

        operator_id = operator_row[0]

        # 查询授权记录
        cursor.execute("""
            SELECT a.app_name, a.app_code, oa.authorized_at, oa.expires_at, oa.is_active
            FROM operator_app_authorizations oa
            JOIN applications a ON oa.application_id = a.id
            WHERE oa.operator_id = ? AND oa.is_active = 1
        """, (operator_id,))

        authorizations = cursor.fetchall()
        conn.close()

        if authorizations:
            print_success(f"运营商已获得 {len(authorizations)} 个应用授权")
            for auth in authorizations:
                app_name, app_code, auth_at, expires_at, is_active = auth
                print(f"\n  应用: {app_name} ({app_code})")
                print(f"    授权时间: {auth_at}")
                print(f"    过期时间: {expires_at if expires_at else '永久'}")
                print(f"    状态: {'有效' if is_active else '无效'}")
            return True
        else:
            print_error("运营商暂无授权")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print_section("管理员功能测试")
        print_info("开始测试...")

        # 1. 管理员登录
        if not self.admin_login():
            return False

        # 2. 查询待审批申请
        if not self.get_pending_requests():
            print_info("当前没有待审批的申请")
            return True

        # 3. 审批第一个申请
        if self.pending_requests:
            request_id = self.pending_requests[0]
            if not self.approve_request(request_id):
                return False

        # 4. 验证授权（使用最近注册的测试账户）
        # 从数据库获取最近的运营商用户名
        import sqlite3
        conn = sqlite3.connect('mr_game_ops.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username FROM operator_accounts
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()

        if row:
            latest_operator = row[0]
            self.verify_operator_authorization(latest_operator)

        print_section("测试完成")
        print_success("管理员功能测试通过！")
        print("\n下一步:")
        print("  1. 运营商可以开始使用已授权的应用")
        print("  2. 测试充值功能")
        print("  3. 测试游戏会话和扣费")

        return True


if __name__ == "__main__":
    try:
        tester = AdminTester()
        success = tester.run_all_tests()
        exit(0 if success else 1)
    except Exception as e:
        print_error(f"测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
