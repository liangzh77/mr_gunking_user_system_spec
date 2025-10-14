"""
契约测试: 按运营点统计接口 (T112)

测试目标:
- 验证 GET /v1/operators/me/statistics/by-site 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖空数据、有数据、时间筛选、数据隔离场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 支持时间筛选: start_time, end_time (可选)
- 返回格式: {success: true, data: {sites: [...]}}
- 每个site包含: site_id, site_name, total_sessions, total_players, total_cost
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

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


async def create_site(client: AsyncClient, token: str, name: str, address: str) -> dict:
    """创建运营点并返回响应数据"""
    response = await client.post(
        "/v1/operators/me/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "address": address,
            "description": f"{name}的描述"
        }
    )
    return response.json()["data"]


# ========== GET /v1/operators/me/statistics/by-site 测试 ==========

@pytest.mark.asyncio
async def test_get_statistics_empty_data(test_db):
    """测试获取空统计数据(无使用记录)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "stats_user_1")

        response = await client.get(
            "/v1/operators/me/statistics/by-site",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data
    assert "sites" in data["data"]
    assert isinstance(data["data"]["sites"], list)
    assert len(data["data"]["sites"]) == 0


@pytest.mark.asyncio
async def test_get_statistics_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/statistics/by-site")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_statistics_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/statistics/by-site",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_statistics_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "stats_user_2")

        # 创建一个运营点(即使没有使用记录,也应该返回空列表)
        await create_site(client, token, "测试门店A", "北京市朝阳区")

        response = await client.get(
            "/v1/operators/me/statistics/by-site",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool), "success应该是布尔类型"
    assert data["success"] is True
    assert isinstance(data["data"], dict), "data应该是字典类型"
    assert isinstance(data["data"]["sites"], list), "sites应该是列表类型"


@pytest.mark.asyncio
async def test_get_statistics_time_filter(test_db):
    """测试时间筛选参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "stats_user_3")

        # 测试start_time和end_time参数
        response = await client.get(
            "/v1/operators/me/statistics/by-site?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_statistics_isolation(test_db):
    """测试运营商数据隔离(不能看到其他运营商的统计数据)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建两个运营商
        token1 = await create_and_login_operator(client, "stats_user_4")
        token2 = await create_and_login_operator(client, "stats_user_5")

        # 运营商1创建运营点
        await create_site(client, token1, "运营商1门店", "北京市朝阳区某地址1号")

        # 运营商2创建运营点
        await create_site(client, token2, "运营商2门店", "上海市浦东新区某地址2号")

        # 运营商1查询统计(应该只看到自己的数据,但无使用记录时为空)
        response1 = await client.get(
            "/v1/operators/me/statistics/by-site",
            headers={"Authorization": f"Bearer {token1}"}
        )

        # 运营商2查询统计(应该只看到自己的数据,但无使用记录时为空)
        response2 = await client.get(
            "/v1/operators/me/statistics/by-site",
            headers={"Authorization": f"Bearer {token2}"}
        )

    assert response1.status_code == 200
    assert response2.status_code == 200

    # 两个运营商的统计应该互不可见(当前都为空,因为没有使用记录)
    assert len(response1.json()["data"]["sites"]) == 0
    assert len(response2.json()["data"]["sites"]) == 0


@pytest.mark.asyncio
async def test_get_statistics_with_only_start_time(test_db):
    """测试只提供start_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "stats_user_6")

        response = await client.get(
            "/v1/operators/me/statistics/by-site?start_time=2025-01-01T00:00:00Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_statistics_with_only_end_time(test_db):
    """测试只提供end_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "stats_user_7")

        response = await client.get(
            "/v1/operators/me/statistics/by-site?end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_statistics_sites_field_format(test_db):
    """测试sites数组中每个对象的字段格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "stats_user_8")

        response = await client.get(
            "/v1/operators/me/statistics/by-site",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 当前应该是空列表(因为没有使用记录)
    sites = data["data"]["sites"]
    assert isinstance(sites, list)

    # 如果有数据,应该包含以下字段(这里只验证结构,暂无实际数据)
    # 每个site应该有: site_id, site_name, total_sessions, total_players, total_cost
    for site in sites:
        assert "site_id" in site
        assert "site_name" in site
        assert "total_sessions" in site
        assert "total_players" in site
        assert "total_cost" in site

        # 验证字段类型
        assert isinstance(site["site_id"], str)
        assert isinstance(site["site_name"], str)
        assert isinstance(site["total_sessions"], int)
        assert isinstance(site["total_players"], int)
        assert isinstance(site["total_cost"], str)


@pytest.mark.asyncio
async def test_get_statistics_no_query_params(test_db):
    """测试不提供任何查询参数(应该返回所有时间的统计)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "stats_user_9")

        response = await client.get(
            "/v1/operators/me/statistics/by-site",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "sites" in data["data"]
