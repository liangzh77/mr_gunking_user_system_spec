"""
契约测试：运营商退款记录查询接口 (T075)

测试目标:
- 验证 GET /v1/operators/me/refunds 接口契约
- 确保请求/响应格式符合契约定义
- 覆盖分页、认证场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 支持分页查询 (page, page_size)
- 返回退款记录列表(分页响应)
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


# ========== GET /v1/operators/me/refunds 测试 ==========

@pytest.mark.asyncio
async def test_get_refunds_success_empty(test_db):
    """测试成功获取空退款记录列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_1")

        response = await client.get(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证分页响应结构
    assert "page" in data
    assert data["page"] == 1
    assert "page_size" in data
    assert data["page_size"] == 20  # 默认值
    assert "total" in data
    assert data["total"] == 0  # 新注册用户无退款记录
    assert "items" in data
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_refunds_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/refunds")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_refunds_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/refunds",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_refunds_pagination(test_db):
    """测试分页参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_2")

        # 测试自定义分页参数
        response = await client.get(
            "/v1/operators/me/refunds?page=2&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_get_refunds_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_3")

        response = await client.get(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证分页字段
    required_fields = ["page", "page_size", "total", "items"]
    for field in required_fields:
        assert field in data, f"缺少必需字段: {field}"

    # 验证数据类型
    assert isinstance(data["page"], int), "page应该是整数类型"
    assert isinstance(data["page_size"], int), "page_size应该是整数类型"
    assert isinstance(data["total"], int), "total应该是整数类型"
    assert isinstance(data["items"], list), "items应该是列表类型"


@pytest.mark.asyncio
async def test_get_refunds_item_format(test_db):
    """测试退款记录项的格式(如果有数据)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_4")

        response = await client.get(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 如果有退款记录,验证item格式
    if data["items"]:
        item = data["items"][0]
        required_item_fields = [
            "refund_id", "requested_amount", "status",
            "reason", "created_at"
        ]
        for field in required_item_fields:
            assert field in item, f"退款记录缺少必需字段: {field}"

        # 验证status枚举值
        assert item["status"] in ["pending", "approved", "rejected"], \
            f"无效的状态: {item['status']}"

        # 验证金额是字符串
        assert isinstance(item["requested_amount"], str), "requested_amount应该是字符串"

        # 如果有实际退款金额,也应该是字符串
        if item.get("actual_refund_amount"):
            assert isinstance(item["actual_refund_amount"], str), \
                "actual_refund_amount应该是字符串"


@pytest.mark.asyncio
async def test_get_refunds_invalid_page(test_db):
    """测试无效的分页参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_5")

        # 测试负数页码(应返回400或422)
        response = await client.get(
            "/v1/operators/me/refunds?page=-1",
            headers={"Authorization": f"Bearer {token}"}
        )

    # FastAPI的Query validation会返回422
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_refunds_invalid_page_size(test_db):
    """测试无效的page_size参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_6")

        # 测试超出范围的page_size(应返回422)
        response = await client.get(
            "/v1/operators/me/refunds?page_size=200",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code in [400, 422]
