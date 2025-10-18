"""
契约测试: 财务仪表盘API (T156)

测试目标:
- 验证财务仪表盘API端点契约
- 确保请求/响应格式符合contract定义
- 覆盖今日概览、趋势分析、大客户查询场景

契约要求:
- GET /finance/dashboard: 今日收入概览
- GET /finance/dashboard/trends: 本月收入趋势
- GET /finance/top-customers: TOP客户列表
- GET /finance/customers/{operator_id}/details: 客户详细财务信息
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from decimal import Decimal

from src.main import app
from src.models.finance import FinanceAccount
from src.models.operator import OperatorAccount
from src.models.transaction import TransactionRecord
from src.core.utils.password import hash_password
from datetime import datetime, timedelta


# ========== Fixtures ==========

@pytest.fixture
async def create_finance_account(test_db):
    """创建财务测试账户"""
    finance = FinanceAccount(
        id=uuid4(),
        username="finance_zhang",
        password_hash=hash_password("FinancePass123"),
        full_name="张财务",
        email="finance.zhang@test.com",
        phone="13900139000",
        role="specialist"
    )
    test_db.add(finance)
    await test_db.commit()
    await test_db.refresh(finance)
    return finance


@pytest.fixture
async def create_test_operator(test_db):
    """创建测试运营商"""
    operator = OperatorAccount(
        id=uuid4(),
        username="test_operator",
        password_hash=hash_password("Pass123"),
        full_name="测试运营商公司",
        phone="13800138001",
        email="test@example.com",
        api_key="test_api_key_12345678901234567890",
        api_key_hash=hash_password("test_api_key_12345678901234567890"),
        balance=Decimal("1000.00"),
        customer_tier="standard"
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)
    return operator


@pytest.fixture
async def create_test_transactions(test_db, create_test_operator):
    """创建测试交易记录"""
    operator = create_test_operator
    today = datetime.now()

    # 今日充值记录
    tx1 = TransactionRecord(
        id=uuid4(),
        operator_id=operator.id,
        transaction_type="recharge",
        amount=Decimal("500.00"),
        balance_after=Decimal("1500.00"),
        description="微信支付充值",
        created_at=today
    )

    # 今日消费记录
    tx2 = TransactionRecord(
        id=uuid4(),
        operator_id=operator.id,
        transaction_type="consumption",
        amount=Decimal("200.00"),
        balance_after=Decimal("1300.00"),
        description="游戏扣费",
        created_at=today
    )

    # 昨日交易
    yesterday = today - timedelta(days=1)
    tx3 = TransactionRecord(
        id=uuid4(),
        operator_id=operator.id,
        transaction_type="recharge",
        amount=Decimal("300.00"),
        balance_after=Decimal("800.00"),
        description="支付宝充值",
        created_at=yesterday
    )

    test_db.add_all([tx1, tx2, tx3])
    await test_db.commit()
    return [tx1, tx2, tx3]


# ========== 辅助函数 ==========

async def finance_login(client: AsyncClient) -> str:
    """财务人员登录,返回JWT Token"""
    response = await client.post(
        "/v1/auth/finance/login",
        json={
            "username": "finance_zhang",
            "password": "FinancePass123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return ""


# ========== GET /finance/dashboard 测试 ==========

@pytest.mark.asyncio
async def test_get_finance_dashboard_success(test_db, create_finance_account, create_test_transactions):
    """测试获取今日收入概览"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构 - 直接字段
    assert "today_recharge" in data
    assert "today_consumption" in data
    assert "today_refund" in data
    assert "today_net_income" in data
    assert "total_operators" in data
    assert "active_operators_today" in data

    # 验证数据类型
    assert isinstance(data["total_operators"], int)
    assert isinstance(data["active_operators_today"], int)


@pytest.mark.asyncio
async def test_get_finance_dashboard_without_token(test_db):
    """测试未提供Token获取仪表盘"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/finance/dashboard")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_finance_dashboard_invalid_token(test_db):
    """测试无效Token获取仪表盘"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/finance/dashboard",
            headers={"Authorization": "Bearer invalid_token"}
        )

    assert response.status_code == 401


# ========== GET /finance/dashboard/trends 测试 ==========

@pytest.mark.asyncio
async def test_get_finance_trends_current_month(test_db, create_finance_account, create_test_transactions):
    """测试获取当前月趋势"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/dashboard/trends",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "month" in data
    assert "chart_data" in data
    assert "summary" in data

    # 验证chart_data是数组
    assert isinstance(data["chart_data"], list)

    # 验证summary结构
    summary = data["summary"]
    assert "total_recharge" in summary
    assert "total_consumption" in summary
    assert "total_refund" in summary
    assert "total_net_income" in summary


@pytest.mark.asyncio
async def test_get_finance_trends_specific_month(test_db, create_finance_account, create_test_transactions):
    """测试获取指定月份趋势"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/dashboard/trends?month=2025-01",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证返回的月份
    assert data["month"] == "2025-01"


@pytest.mark.asyncio
async def test_get_finance_trends_invalid_month_format(test_db, create_finance_account):
    """测试无效月份格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/dashboard/trends?month=invalid",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 应该返回格式错误
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_finance_trends_without_token(test_db):
    """测试未提供Token获取趋势"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/finance/dashboard/trends")

    assert response.status_code == 401


# ========== GET /finance/top-customers 测试 ==========

@pytest.mark.asyncio
async def test_get_top_customers_default(test_db, create_finance_account, create_test_operator):
    """测试获取TOP客户(默认限制)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/top-customers",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "customers" in data
    assert "total_consumption" in data
    assert isinstance(data["customers"], list)

    # 如果有客户数据,验证结构
    if len(data["customers"]) > 0:
        customer = data["customers"][0]
        assert "rank" in customer
        assert "operator_id" in customer
        assert "operator_name" in customer
        assert "category" in customer
        assert "total_consumption" in customer
        assert "consumption_percentage" in customer
        assert "total_sessions" in customer


@pytest.mark.asyncio
async def test_get_top_customers_with_limit(test_db, create_finance_account, create_test_operator):
    """测试获取TOP客户(自定义限制)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/top-customers?limit=5",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["customers"], list)
    assert len(data["customers"]) <= 5


@pytest.mark.asyncio
async def test_get_top_customers_invalid_limit(test_db, create_finance_account):
    """测试无效的limit参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        # limit > 100
        response = await client.get(
            "/v1/finance/top-customers?limit=200",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_top_customers_with_time_range(test_db, create_finance_account, create_test_operator):
    """测试带时间范围的TOP客户查询"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/top-customers?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_top_customers_without_token(test_db):
    """测试未提供Token获取TOP客户"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/finance/top-customers")

    assert response.status_code == 401


# ========== GET /finance/customers/{operator_id}/details 测试 ==========

@pytest.mark.asyncio
async def test_get_customer_details_success(test_db, create_finance_account, create_test_operator):
    """测试获取客户财务详情"""
    operator = create_test_operator

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            f"/v1/finance/customers/{operator.id}/details",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "operator_id" in data
    assert "operator_name" in data
    assert "category" in data
    assert "current_balance" in data
    assert "total_recharged" in data
    assert "total_consumed" in data
    assert "total_refunded" in data
    assert "total_sessions" in data
    assert "first_transaction_at" in data


@pytest.mark.asyncio
async def test_get_customer_details_nonexistent(test_db, create_finance_account):
    """测试获取不存在客户的详情"""
    fake_id = uuid4()

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            f"/v1/finance/customers/{fake_id}/details",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_customer_details_invalid_id(test_db, create_finance_account):
    """测试无效的运营商ID"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/customers/invalid_id/details",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_customer_details_without_token(test_db, create_test_operator):
    """测试未提供Token获取客户详情"""
    operator = create_test_operator

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/v1/finance/customers/{operator.id}/details")

    assert response.status_code == 401
