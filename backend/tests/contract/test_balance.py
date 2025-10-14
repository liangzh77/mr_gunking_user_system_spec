"""
契约测试：运营商余额查询接口 (T072)

测试目标:
- 验证 GET /v1/operators/me/balance 接口契约
- 确保请求/响应格式符合契约定义
- 覆盖认证、授权场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 返回当前运营商的账户余额信息
"""
import pytest
from httpx import AsyncClient

from src.main import app


# ========== 辅助函数 ==========

async def create_and_login_operator(client: AsyncClient, username: str) -> str:
    """创建运营商并登录,返回JWT Token"""
    # 注册
    await client.post(
        "/v1/auth/operators/register",
        json={
            "username": username,
            "password": "TestPass123",
            "name": "测试公司",
            "phone": "13800138000",
            "email": f"{username}@example.com"
        }
    )

    # 登录
    response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "TestPass123"
        }
    )

    return response.json()["data"]["access_token"]


# ========== GET /v1/operators/me/balance 测试 ==========

@pytest.mark.asyncio
async def test_get_balance_success(test_db):
    """测试成功获取余额信息"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "balance_user_1")

        response = await client.get(
            "/v1/operators/me/balance",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "balance" in data
    assert data["balance"] == "0.00"  # 新注册用户余额为0
    assert "category" in data
    assert data["category"] == "trial"  # 新注册默认试用


@pytest.mark.asyncio
async def test_get_balance_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/balance")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_balance_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/balance",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_balance_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "balance_user_2")

        response = await client.get(
            "/v1/operators/me/balance",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证必需字段存在
    required_fields = ["balance", "category"]
    for field in required_fields:
        assert field in data, f"缺少必需字段: {field}"

    # 验证数据类型
    assert isinstance(data["balance"], str), "balance应该是字符串类型"
    assert isinstance(data["category"], str), "category应该是字符串类型"

    # 验证category值合法
    assert data["category"] in ["trial", "normal", "vip"], f"无效的category值: {data['category']}"
