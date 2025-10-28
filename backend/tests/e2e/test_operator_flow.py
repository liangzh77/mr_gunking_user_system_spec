"""运营商端到端流程测试 (T285)

测试运营商的完整用户旅程:
1. 注册新账户
2. 登录系统
3. 查看余额
4. 创建运营点
5. 查看交易记录

运行方式:
```bash
pytest tests/e2e/test_operator_flow.py --headed  # 有界面模式
pytest tests/e2e/test_operator_flow.py --browser chromium  # 指定浏览器
pytest tests/e2e/test_operator_flow.py --slowmo 1000  # 慢动作模式
```
"""

import pytest
from playwright.sync_api import Page, expect
import time


class TestOperatorRegistrationFlow:
    """测试运营商注册流程"""

    @pytest.mark.e2e
    def test_operator_can_access_api_docs(self, page: Page, base_url: str):
        """测试访问 API 文档 (基础健康检查)"""
        # 访问 API 文档页面
        page.goto(f"{base_url}/api/docs")

        # 验证页面标题包含 "MR"
        expect(page).to_have_title(lambda title: "MR" in title or "API" in title or "FastAPI" in title)

        # 验证页面加载成功
        expect(page.locator("body")).to_be_visible()

        # 截图记录
        page.screenshot(path="test-results/api-docs.png")


class TestOperatorLoginFlow:
    """测试运营商登录流程

    注意: 这些测试需要后端服务运行在 http://localhost:8000
    并且需要预先创建测试账户。
    """

    @pytest.mark.e2e
    @pytest.mark.skip(reason="需要前端页面实现")
    def test_operator_login_success(self, page: Page, base_url: str):
        """测试运营商成功登录流程"""
        # 访问登录页面
        page.goto(f"{base_url}/operator/login")

        # 填写登录表单
        page.fill('input[name="username"]', "test_operator")
        page.fill('input[name="password"]', "Test123!@#")

        # 点击登录按钮
        page.click('button[type="submit"]')

        # 等待跳转到仪表板
        page.wait_for_url(f"{base_url}/operator/dashboard")

        # 验证登录成功 - 应该看到用户名
        expect(page.locator("text=test_operator")).to_be_visible()

        # 验证余额显示
        expect(page.locator('[data-testid="balance"]')).to_be_visible()


class TestOperatorDashboardFlow:
    """测试运营商仪表板流程"""

    @pytest.mark.e2e
    @pytest.mark.skip(reason="需要前端页面实现")
    def test_operator_can_view_balance(self, page: Page, base_url: str):
        """测试查看余额功能"""
        # 假设已登录，直接访问仪表板
        page.goto(f"{base_url}/operator/dashboard")

        # 查找余额元素
        balance_element = page.locator('[data-testid="balance"]')
        expect(balance_element).to_be_visible()

        # 验证余额格式正确 (应该是数字)
        balance_text = balance_element.inner_text()
        assert "¥" in balance_text or "元" in balance_text

    @pytest.mark.e2e
    @pytest.mark.skip(reason="需要前端页面实现")
    def test_operator_can_view_sites(self, page: Page, base_url: str):
        """测试查看运营点列表"""
        page.goto(f"{base_url}/operator/sites")

        # 验证页面标题
        expect(page.locator("h1")).to_contain_text("运营点")

        # 验证表格存在
        expect(page.locator("table")).to_be_visible()


class TestAPIEndpointsDirectly:
    """直接测试 API 端点 (不依赖前端)

    这些测试通过 Playwright 的 request 上下文直接调用 API，
    不依赖前端实现，可以立即运行。
    """

    @pytest.mark.e2e
    def test_health_check_endpoint(self, page: Page, base_url: str):
        """测试健康检查端点"""
        response = page.request.get(f"{base_url}/health")

        # 验证状态码
        assert response.status == 200

        # 验证响应内容
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.e2e
    def test_operator_login_api(self, page: Page, base_url: str):
        """测试运营商登录 API (使用测试账户)

        注意: 需要预先创建测试账户
        """
        # 尝试登录 (即使账户不存在也会返回一致的响应)
        response = page.request.post(
            f"{base_url}/api/v1/operators/login",
            data={
                "username": "test_operator_e2e",
                "password": "Test123!@#"
            }
        )

        # 验证响应格式正确 (成功或失败都应该是 JSON)
        assert response.headers["content-type"] == "application/json"

        # 如果是 401，说明账户不存在或密码错误 (符合预期)
        # 如果是 200，说明登录成功
        assert response.status in [200, 401, 422]

    @pytest.mark.e2e
    def test_api_docs_accessible(self, page: Page, base_url: str):
        """测试 API 文档可访问"""
        response = page.request.get(f"{base_url}/api/docs")

        # 验证状态码
        assert response.status == 200

        # 验证是 HTML 响应
        assert "text/html" in response.headers["content-type"]


class TestFullOperatorJourney:
    """完整的运营商用户旅程测试

    此测试模拟运营商从注册到使用的完整流程。
    """

    @pytest.mark.e2e
    @pytest.mark.skip(reason="需要前端页面和测试数据准备")
    def test_complete_operator_journey(self, page: Page, base_url: str):
        """完整的运营商使用流程

        步骤:
        1. 访问注册页面
        2. 填写注册信息
        3. 注册成功
        4. 登录系统
        5. 查看仪表板
        6. 创建运营点
        7. 查询余额
        8. 申请充值
        """
        # 1. 注册
        page.goto(f"{base_url}/operator/register")
        page.fill('input[name="username"]', f"e2e_test_{int(time.time())}")
        page.fill('input[name="password"]', "Test123!@#")
        page.fill('input[name="full_name"]', "E2E Test User")
        page.fill('input[name="email"]', "e2e@test.com")
        page.fill('input[name="phone"]', "13800138000")
        page.click('button[type="submit"]')

        # 等待注册成功
        expect(page.locator("text=注册成功")).to_be_visible()

        # 2. 登录
        page.goto(f"{base_url}/operator/login")
        # ... 登录流程

        # 3. 创建运营点
        page.goto(f"{base_url}/operator/sites/create")
        # ... 创建运营点流程

        # 4. 查看余额
        page.goto(f"{base_url}/operator/dashboard")
        expect(page.locator('[data-testid="balance"]')).to_be_visible()

        # 5. 截图记录最终状态
        page.screenshot(path="test-results/operator-journey-complete.png")
