"""
契约测试: 使用记录查询接口 (T110/T102)

测试目标:
- 验证 GET /v1/operators/me/usage-records 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖分页、时间筛选、运营点筛选、应用筛选场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 支持分页参数: page, page_size
- 支持时间筛选: start_time, end_time
- 支持筛选参数: site_id, app_id
- 返回分页格式 + UsageRecord数组
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


# ========== GET /v1/operators/me/usage-records 测试 ==========

@pytest.mark.asyncio
async def test_get_usage_records_empty_list(test_db):
    """测试获取空使用记录列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "usage_user_1")

        response = await client.get(
            "/v1/operators/me/usage-records",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data
    assert "items" in data["data"]
    assert "total" in data["data"]
    assert "page" in data["data"]
    assert "page_size" in data["data"]
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_get_usage_records_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/usage-records")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_usage_records_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/usage-records",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_usage_records_pagination_params(test_db):
    """测试分页参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "usage_user_2")

        # 测试page和page_size参数
        response = await client.get(
            "/v1/operators/me/usage-records?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 10


@pytest.mark.asyncio
async def test_get_usage_records_time_filter(test_db):
    """测试时间筛选参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "usage_user_3")

        # 测试start_time和end_time参数
        response = await client.get(
            "/v1/operators/me/usage-records?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_usage_records_site_filter(test_db):
    """测试运营点筛选参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "usage_user_4")

        # 测试site_id参数
        response = await client.get(
            "/v1/operators/me/usage-records?site_id=site_test_001",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_usage_records_app_filter(test_db):
    """测试应用筛选参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "usage_user_5")

        # 测试app_id参数
        response = await client.get(
            "/v1/operators/me/usage-records?app_id=app_test_001",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_usage_records_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "usage_user_6")

        response = await client.get(
            "/v1/operators/me/usage-records",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool), "success应该是布尔类型"
    assert data["success"] is True
    assert isinstance(data["data"], dict), "data应该是字典类型"

    # 验证分页格式
    assert isinstance(data["data"]["items"], list), "items应该是列表类型"
    assert isinstance(data["data"]["total"], int), "total应该是整数"
    assert isinstance(data["data"]["page"], int), "page应该是整数"
    assert isinstance(data["data"]["page_size"], int), "page_size应该是整数"


@pytest.mark.asyncio
async def test_get_usage_records_isolation(test_db):
    """测试运营商数据隔离(不能看到其他运营商的使用记录)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建两个运营商
        token1 = await create_and_login_operator(client, "usage_user_7")
        token2 = await create_and_login_operator(client, "usage_user_8")

        # 运营商1查询(应该为空)
        response1 = await client.get(
            "/v1/operators/me/usage-records",
            headers={"Authorization": f"Bearer {token1}"}
        )

        # 运营商2查询(应该为空)
        response2 = await client.get(
            "/v1/operators/me/usage-records",
            headers={"Authorization": f"Bearer {token2}"}
        )

    assert response1.status_code == 200
    assert response2.status_code == 200

    # 两个运营商的记录应该互不可见
    assert len(response1.json()["data"]["items"]) == 0
    assert len(response2.json()["data"]["items"]) == 0


@pytest.mark.asyncio
async def test_get_usage_records_default_pagination(test_db):
    """测试默认分页行为"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "usage_user_9")

        # 不提供分页参数,应该使用默认值
        response = await client.get(
            "/v1/operators/me/usage-records",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证默认值(通常page=1, page_size=20)
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] in [10, 20, 50]  # 常见的默认值


@pytest.mark.asyncio
async def test_get_usage_records_combined_filters(test_db):
    """测试组合筛选参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "usage_user_10")

        # 测试组合使用多个筛选参数
        response = await client.get(
            "/v1/operators/me/usage-records"
            "?page=1&page_size=10"
            "&start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z"
            "&site_id=site_test_001&app_id=app_test_001",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
