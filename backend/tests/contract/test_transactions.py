"""
契约测试：运营商交易记录查询接口 (T073)

测试目标:
- 验证 GET /v1/operators/me/transactions 接口契约
- 确保请求/响应格式符合契约定义
- 覆盖分页、过滤、认证场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 支持分页查询 (page, page_size)
- 支持时间范围过滤 (start_time, end_time)
- 支持交易类型过滤 (type: recharge/consumption/all)
- 返回交易记录列表(分页响应)
"""
import pytest
from datetime import datetime, timezone, timedelta
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


# ========== GET /v1/operators/me/transactions 测试 ==========

@pytest.mark.asyncio
async def test_get_transactions_success_empty(test_db):
    """测试成功获取空交易记录列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "trans_user_1")

        response = await client.get(
            "/v1/operators/me/transactions",
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
    assert data["total"] == 0  # 新注册用户无交易记录
    assert "items" in data
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_transactions_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/transactions")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_transactions_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/transactions",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_transactions_pagination(test_db):
    """测试分页参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "trans_user_2")

        # 测试自定义分页参数
        response = await client.get(
            "/v1/operators/me/transactions?page=2&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_get_transactions_filter_by_type(test_db):
    """测试交易类型过滤参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "trans_user_3")

        # 测试type参数
        for trans_type in ["all", "recharge", "consumption"]:
            response = await client.get(
                f"/v1/operators/me/transactions?type={trans_type}",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "items" in data


@pytest.mark.asyncio
async def test_get_transactions_filter_by_time(test_db):
    """测试时间范围过滤参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "trans_user_4")

        # 测试时间范围参数(使用isoformat()和replace确保格式正确)
        start_time = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat().replace('+00:00', 'Z')
        end_time = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        response = await client.get(
            f"/v1/operators/me/transactions?start_time={start_time}&end_time={end_time}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_get_transactions_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "trans_user_5")

        response = await client.get(
            "/v1/operators/me/transactions",
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
async def test_get_transactions_item_format(test_db):
    """测试交易记录项的格式(如果有数据)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "trans_user_6")

        response = await client.get(
            "/v1/operators/me/transactions",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 如果有交易记录,验证item格式
    if data["items"]:
        item = data["items"][0]
        required_item_fields = [
            "transaction_id", "type", "amount",
            "balance_after", "created_at"
        ]
        for field in required_item_fields:
            assert field in item, f"交易记录缺少必需字段: {field}"

        # 验证type枚举值
        assert item["type"] in ["recharge", "consumption"], \
            f"无效的交易类型: {item['type']}"

        # 验证金额和余额是字符串
        assert isinstance(item["amount"], str), "amount应该是字符串"
        assert isinstance(item["balance_after"], str), "balance_after应该是字符串"


@pytest.mark.asyncio
async def test_get_transactions_invalid_page(test_db):
    """测试无效的分页参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "trans_user_7")

        # 测试负数页码(应返回400)
        response = await client.get(
            "/v1/operators/me/transactions?page=-1",
            headers={"Authorization": f"Bearer {token}"}
        )

    # FastAPI的Query validation会返回422
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_transactions_invalid_type(test_db):
    """测试无效的交易类型参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "trans_user_8")

        # 测试非法type值
        response = await client.get(
            "/v1/operators/me/transactions?type=invalid_type",
            headers={"Authorization": f"Bearer {token}"}
        )

    # FastAPI的Query validation会返回422
    assert response.status_code in [400, 422]
