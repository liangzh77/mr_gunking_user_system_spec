"""
契约测试: 按应用统计接口 (T113)

测试目标:
- 验证 GET /v1/operators/me/statistics/by-app 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖空数据、时间筛选、数据隔离、响应格式场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 支持时间筛选: start_time, end_time (可选)
- 返回格式: {success: true, data: {applications: [...]}}
- 每个application包含: app_id, app_name, total_sessions, total_players, avg_players_per_session, total_cost
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


# ========== GET /v1/operators/me/statistics/by-app 测试 ==========

@pytest.mark.asyncio
async def test_get_statistics_by_app_empty_data(test_db):
    """测试获取空统计数据(无使用记录)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_stats_user_1")

        response = await client.get(
            "/v1/operators/me/statistics/by-app",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data
    assert "applications" in data["data"]
    assert isinstance(data["data"]["applications"], list)
    assert len(data["data"]["applications"]) == 0


@pytest.mark.asyncio
async def test_get_statistics_by_app_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/statistics/by-app")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_statistics_by_app_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/statistics/by-app",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_statistics_by_app_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_stats_user_2")

        response = await client.get(
            "/v1/operators/me/statistics/by-app",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool), "success应该是布尔类型"
    assert data["success"] is True
    assert isinstance(data["data"], dict), "data应该是字典类型"
    assert isinstance(data["data"]["applications"], list), "applications应该是列表类型"


@pytest.mark.asyncio
async def test_get_statistics_by_app_time_filter(test_db):
    """测试时间筛选参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_stats_user_3")

        # 测试start_time和end_time参数
        response = await client.get(
            "/v1/operators/me/statistics/by-app?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_statistics_by_app_isolation(test_db):
    """测试运营商数据隔离(不能看到其他运营商的统计数据)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建两个运营商
        token1 = await create_and_login_operator(client, "app_stats_user_4")
        token2 = await create_and_login_operator(client, "app_stats_user_5")

        # 运营商1查询统计(应该只看到自己的数据,但无使用记录时为空)
        response1 = await client.get(
            "/v1/operators/me/statistics/by-app",
            headers={"Authorization": f"Bearer {token1}"}
        )

        # 运营商2查询统计(应该只看到自己的数据,但无使用记录时为空)
        response2 = await client.get(
            "/v1/operators/me/statistics/by-app",
            headers={"Authorization": f"Bearer {token2}"}
        )

    assert response1.status_code == 200
    assert response2.status_code == 200

    # 两个运营商的统计应该互不可见(当前都为空,因为没有使用记录)
    assert len(response1.json()["data"]["applications"]) == 0
    assert len(response2.json()["data"]["applications"]) == 0


@pytest.mark.asyncio
async def test_get_statistics_by_app_with_only_start_time(test_db):
    """测试只提供start_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_stats_user_6")

        response = await client.get(
            "/v1/operators/me/statistics/by-app?start_time=2025-01-01T00:00:00Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_statistics_by_app_with_only_end_time(test_db):
    """测试只提供end_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_stats_user_7")

        response = await client.get(
            "/v1/operators/me/statistics/by-app?end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_statistics_by_app_applications_field_format(test_db):
    """测试applications数组中每个对象的字段格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_stats_user_8")

        response = await client.get(
            "/v1/operators/me/statistics/by-app",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 当前应该是空列表(因为没有使用记录)
    applications = data["data"]["applications"]
    assert isinstance(applications, list)

    # 如果有数据,应该包含以下字段(这里只验证结构,暂无实际数据)
    # 每个application应该有: app_id, app_name, total_sessions, total_players, avg_players_per_session, total_cost
    for application in applications:
        assert "app_id" in application
        assert "app_name" in application
        assert "total_sessions" in application
        assert "total_players" in application
        assert "avg_players_per_session" in application
        assert "total_cost" in application

        # 验证字段类型
        assert isinstance(application["app_id"], str)
        assert isinstance(application["app_name"], str)
        assert isinstance(application["total_sessions"], int)
        assert isinstance(application["total_players"], int)
        assert isinstance(application["avg_players_per_session"], (int, float))
        assert isinstance(application["total_cost"], str)


@pytest.mark.asyncio
async def test_get_statistics_by_app_no_query_params(test_db):
    """测试不提供任何查询参数(应该返回所有时间的统计)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_stats_user_9")

        response = await client.get(
            "/v1/operators/me/statistics/by-app",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "applications" in data["data"]


@pytest.mark.asyncio
async def test_get_statistics_by_app_avg_players_calculation(test_db):
    """测试平均每场玩家数的计算(验证契约中的avg_players_per_session字段)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_stats_user_10")

        response = await client.get(
            "/v1/operators/me/statistics/by-app",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证每个应用都包含 avg_players_per_session 字段
    applications = data["data"]["applications"]
    for application in applications:
        assert "avg_players_per_session" in application
        assert isinstance(application["avg_players_per_session"], (int, float))

        # 如果有数据,验证计算逻辑: avg = total_players / total_sessions
        if application["total_sessions"] > 0:
            expected_avg = application["total_players"] / application["total_sessions"]
            # 允许1位小数的舍入误差
            assert abs(application["avg_players_per_session"] - expected_avg) < 0.2
