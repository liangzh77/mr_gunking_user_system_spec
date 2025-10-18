"""
契约测试: 财务人员登录API (T155)

测试目标:
- 验证财务人员登录API端点契约
- 确保请求/响应格式符合contract定义
- 覆盖登录、认证、错误处理场景

契约要求:
- POST /auth/finance/login: 财务人员登录
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.main import app
from src.models.finance import FinanceAccount
from src.core.utils.password import hash_password


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


# ========== 辅助函数 ==========

async def finance_login(client: AsyncClient, username: str = "finance_zhang", password: str = "FinancePass123") -> str:
    """财务人员登录,返回JWT Token"""
    response = await client.post(
        "/v1/auth/finance/login",
        json={
            "username": username,
            "password": password
        }
    )

    if response.status_code == 200:
        return response.json()["access_token"]  # 直接访问access_token
    return ""


# ========== POST /auth/finance/login 测试 ==========

@pytest.mark.asyncio
async def test_finance_login_success(test_db, create_finance_account):
    """测试财务人员成功登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "username": "finance_zhang",
                "password": "FinancePass123"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构 - 直接字段,没有success/data包装
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert "finance" in data

    # 验证财务人员信息
    finance_info = data["finance"]
    assert finance_info["username"] == "finance_zhang"
    assert "finance_id" in finance_info
    assert "name" in finance_info
    assert "role" in finance_info
    assert finance_info["role"] == "finance"

    # 验证token格式正确(JWT格式)
    assert len(data["access_token"]) > 100  # JWT token应该很长
    assert data["access_token"].count('.') == 2  # JWT有3部分用.分隔


@pytest.mark.asyncio
async def test_finance_login_invalid_password(test_db, create_finance_account):
    """测试错误密码登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "username": "finance_zhang",
                "password": "WrongPassword123"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_finance_login_nonexistent_user(test_db, create_finance_account):
    """测试不存在的用户登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "username": "nonexistent_finance",
                "password": "SomePassword123"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_finance_login_missing_username(test_db):
    """测试缺少用户名"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "password": "FinancePass123"
            }
        )

    assert response.status_code in [400, 422]  # Validation error


@pytest.mark.asyncio
async def test_finance_login_missing_password(test_db):
    """测试缺少密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "username": "finance_zhang"
            }
        )

    assert response.status_code in [400, 422]  # Validation error


@pytest.mark.asyncio
async def test_finance_login_empty_username(test_db):
    """测试空用户名"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "username": "",
                "password": "FinancePass123"
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_finance_login_empty_password(test_db):
    """测试空密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "username": "finance_zhang",
                "password": ""
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_finance_login_invalid_content_type(test_db, create_finance_account):
    """测试错误的Content-Type"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/finance/login",
            content="username=finance_zhang&password=FinancePass123",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

    # FastAPI应该拒绝非JSON请求
    assert response.status_code in [400, 415, 422]


@pytest.mark.asyncio
async def test_finance_login_malformed_json(test_db):
    """测试格式错误的JSON"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/finance/login",
            content="{invalid json}",
            headers={"Content-Type": "application/json"}
        )

    assert response.status_code in [400, 422]
